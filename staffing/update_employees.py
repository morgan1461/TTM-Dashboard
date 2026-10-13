"""Biweekly staffing database update.

Takes the Workday Current Worker Detail report and the Workday Termination
report and updates the `employees` table (one row per employee, keyed by
employee ID). The employee ID is the only identifier used to match records
between the two reports (and the optional Training & Staffing Master).

Each run is idempotent: re-running the same reports yields the same database.
After updating employees, the active roster is recorded in `staffing_snapshots`
for the report date so the dashboard trend charts keep working.

Usage:
    python update_employees.py CURRENT_WORKER.xlsx TERMINATIONS.xlsx 2026-07-19 [TRAINING_MASTER.xlsx]
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database.staffing_db import connect, replace_snapshot, _clean_id  # noqa: E402

STUDENT_JOB_FAMILY_GROUP = "Students"
STUDENT_JOB_FAMILY = "Student Employee - Hourly"
EXCLUDED_JOB_FAMILY_GROUP = "Unclassified"
EXCLUDED_JOB_CODE = "STUDENT3"

# Workday column -> employees column
CURRENT_COLS = {
    "ID": "employee_id",
    "Legal Name in General Display Format": "full_name",
    "Legal Name - Last Name": "last_name",
    "Legal Name - First Name": "first_name",
    "Hire Date": "hire_date",
    "Employee Type": "workday_employee_type",
    "FTE": "fte",
    "Job Code": "job_code",
    "Job Family": "job_family",
    "Job Family Group": "job_family_group",
}
TERMINATION_COLS = {
    "ID": "employee_id",
    "Legal Name": "full_name",
    "Last Name": "last_name",
    "First Name": "first_name",
    "Hire Date": "hire_date",
    "Termination Date": "termination_date",
    "Primary Termination Category": "termination_category",
    "Primary Termination Reason": "termination_reason",
    "Employee Type": "workday_employee_type",
    "Job Code": "job_code",
    "Job Family": "job_family",
    "Job Family Group": "job_family_group",
}
TSM_COLS = {
    "Employee ID": "employee_id",
    "Drivers #": "driver_num",
    "Active": "active",
    "Permit": "permit",
    "CDL": "cdl",
    "Student CDL Training Start Date": "cdl_training_start_date",
}
DATE_COLS = ["hire_date", "termination_date", "cdl_training_start_date"]
EMPLOYEE_FIELDS = [
    "employee_type", "last_name", "first_name", "full_name", "hire_date",
    "termination_date", "termination_category", "termination_reason",
    "job_family", "job_family_group", "job_code", "fte",
]


def read_report(path) -> pd.DataFrame:
    """Read a Workday excel export, locating the header row (the one containing 'ID')."""
    raw = pd.read_excel(path, header=None, dtype=object)
    for i in range(min(10, len(raw))):
        if "ID" in raw.iloc[i].astype(str).str.strip().tolist():
            df = raw.iloc[i + 1:].copy()
            df.columns = raw.iloc[i].astype(str).str.strip()
            return df.reset_index(drop=True)
    raise ValueError(f"No header row containing 'ID' found in {path}")


def _select(df: pd.DataFrame, colmap: dict) -> pd.DataFrame:
    if "ID" not in df.columns:
        raise ValueError("Report is missing the 'ID' column.")
    out = df[[c for c in colmap if c in df.columns]].rename(columns=colmap)
    for c in colmap.values():
        if c not in out.columns:
            out[c] = pd.NA
    out["employee_id"] = _clean_id(out["employee_id"])
    out = out[out["employee_id"].notna()]
    for c in DATE_COLS:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%Y-%m-%d")
    for c in out.columns:
        if out[c].dtype == object or str(out[c].dtype) in ("string", "str"):
            if c not in ("fte",):
                out[c] = out[c].astype("string").str.strip()
    return out.drop_duplicates("employee_id", keep="last")


def classify_employee_type(df: pd.DataFrame) -> pd.Series:
    """student / full_time (Regular) / part_time (Intermittent); NA if unknown."""
    status = df["workday_employee_type"].astype("string").str.strip()
    group = df["job_family_group"].astype("string").str.strip()
    emp = pd.Series(pd.NA, index=df.index, dtype="string")
    emp[status.str.contains("Regular", case=False, na=False)] = "full_time"
    emp[status.str.contains("Intermittent", case=False, na=False)] = "part_time"
    emp[group == STUDENT_JOB_FAMILY_GROUP] = "student"
    return emp


def prepare_current(df: pd.DataFrame) -> pd.DataFrame:
    out = _select(df, CURRENT_COLS)
    out["fte"] = pd.to_numeric(out["fte"], errors="coerce")
    out = out[(out["job_family_group"] != EXCLUDED_JOB_FAMILY_GROUP)
              & (out["job_code"] != EXCLUDED_JOB_CODE)]
    out["employee_type"] = classify_employee_type(out)
    unknown = out["employee_type"].isna()
    if unknown.any():
        print(f"Warning: skipping {int(unknown.sum())} current workers with unrecognized employee type: "
              f"{out.loc[unknown, 'employee_id'].tolist()}")
    return out[~unknown].drop(columns="workday_employee_type")


def prepare_terminations(df: pd.DataFrame) -> pd.DataFrame:
    out = _select(df, TERMINATION_COLS)
    out["fte"] = pd.NA
    out = out[out["termination_date"].notna()]
    out = out[out["job_code"] != EXCLUDED_JOB_CODE]
    out["employee_type"] = classify_employee_type(out)
    return out.drop(columns="workday_employee_type")


def prepare_training_master(df: pd.DataFrame) -> pd.DataFrame:
    out = _select(df, TSM_COLS)
    for c in ("driver_num", "active", "permit", "cdl"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out[["employee_id", "driver_num", "active", "permit", "cdl", "cdl_training_start_date"]]


def _val(v):
    return None if pd.isna(v) else v


def apply_current_workers(conn, current: pd.DataFrame, report_date: str) -> int:
    """Upsert everyone on the current worker report. A prior termination date is
    cleared only when the person has been rehired (hire date after termination)."""
    sql = """
    INSERT INTO employees (employee_id, employee_type, last_name, first_name, full_name,
        hire_date, job_family, job_family_group, job_code, fte, last_seen_date)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(employee_id) DO UPDATE SET
        employee_type=excluded.employee_type,
        last_name=excluded.last_name, first_name=excluded.first_name,
        full_name=excluded.full_name, hire_date=excluded.hire_date,
        job_family=excluded.job_family, job_family_group=excluded.job_family_group,
        job_code=excluded.job_code, fte=excluded.fte,
        termination_category=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_category END,
        termination_reason=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_reason END,
        termination_date=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_date END,
        last_seen_date=MAX(excluded.last_seen_date, COALESCE(employees.last_seen_date, '')),
        updated_at=datetime('now')
    """
    rows = [
        tuple(_val(r[c]) for c in ("employee_id", "employee_type", "last_name", "first_name",
                                   "full_name", "hire_date", "job_family", "job_family_group",
                                   "job_code", "fte")) + (report_date,)
        for _, r in current.iterrows()
    ]
    conn.executemany(sql, rows)
    return len(rows)


def apply_terminations(conn, terms: pd.DataFrame) -> tuple:
    """Set termination data by employee ID. Unknown IDs are inserted as terminated
    employees (when their type can be determined). Returns (updated, inserted)."""
    updated = inserted = 0
    for _, r in terms.iterrows():
        eid = r["employee_id"]
        cur = conn.execute(
            """UPDATE employees SET termination_date=?, termination_category=?,
               termination_reason=?, updated_at=datetime('now') WHERE employee_id=?""",
            (_val(r["termination_date"]), _val(r["termination_category"]),
             _val(r["termination_reason"]), eid),
        )
        if cur.rowcount:
            updated += 1
        elif pd.notna(r["employee_type"]):
            conn.execute(
                """INSERT INTO employees (employee_id, employee_type, last_name, first_name,
                   full_name, hire_date, termination_date, termination_category,
                   termination_reason, job_family, job_family_group, job_code)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(_val(r[c]) for c in ("employee_id", "employee_type", "last_name",
                      "first_name", "full_name", "hire_date", "termination_date",
                      "termination_category", "termination_reason", "job_family",
                      "job_family_group", "job_code")),
            )
            inserted += 1
        else:
            print(f"Warning: terminated employee {eid} is unknown and has no recognizable type; skipped.")
    return updated, inserted


def apply_training_master(conn, tsm: pd.DataFrame) -> int:
    n = 0
    for _, r in tsm.iterrows():
        cur = conn.execute(
            """UPDATE employees SET driver_num=?, active=?, permit=?, cdl=?,
               cdl_training_start_date=?, updated_at=datetime('now') WHERE employee_id=?""",
            (_val(r["driver_num"]), _val(r["active"]), _val(r["permit"]), _val(r["cdl"]),
             _val(r["cdl_training_start_date"]), r["employee_id"]),
        )
        n += cur.rowcount
    return n


def record_snapshot(conn, report_date: str, db_path=None) -> int:
    """Store the active roster (seen on the report date and not terminated) as snapshot rows."""
    roster = pd.read_sql_query(
        """SELECT employee_id, employee_type, last_name, first_name, full_name, hire_date,
                  driver_num, active, permit, cdl, cdl_training_start_date
           FROM employees
           WHERE last_seen_date = ? AND (termination_date IS NULL OR termination_date > ?)""",
        conn, params=(report_date, report_date),
    )
    if roster.empty:
        return 0
    is_student = roster["employee_type"] == "student"
    roster["cdl_status"] = "not-applicable"
    roster.loc[is_student, "cdl_status"] = "unknown"
    roster.loc[is_student & (roster["cdl"] == 1), "cdl_status"] = "cdl"
    has_start = roster["cdl_training_start_date"].notna()
    roster.loc[is_student & (roster["cdl"] != 1) & has_start, "cdl_status"] = "training-cdl"
    roster.loc[is_student & (roster["cdl"] == 0) & ~has_start, "cdl_status"] = "non-cdl"
    roster["date"] = report_date
    total = 0
    for emp_type, grp in roster.groupby("employee_type"):
        total += replace_snapshot(grp, emp_type, report_date, db_path=db_path)
    return total


def update_staffing_database(current_path, termination_path, report_date, training_master_path=None,
                             db_path=None) -> dict:
    report_date = pd.to_datetime(report_date).strftime("%Y-%m-%d")
    current = prepare_current(read_report(current_path))
    terms = prepare_terminations(read_report(termination_path))
    tsm = None
    if training_master_path:
        tsm = prepare_training_master(pd.read_excel(training_master_path, sheet_name="Students"))

    with connect(db_path) as conn:
        n_current = apply_current_workers(conn, current, report_date)
        updated, inserted = apply_terminations(conn, terms)
        if tsm is not None:
            apply_training_master(conn, tsm)
    # snapshot rows go in separate transaction(s) after employees are committed
    with connect(db_path) as conn:
        n_snap = record_snapshot(conn, report_date, db_path)
    return {"current_workers": n_current, "terminations_updated": updated,
            "terminations_inserted": inserted, "snapshot_rows": n_snap}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    print(update_staffing_database(sys.argv[1], sys.argv[2], sys.argv[3],
                                   sys.argv[4] if len(sys.argv) > 4 else None))
