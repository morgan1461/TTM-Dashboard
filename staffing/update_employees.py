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
    python update_employees.py --backfill   # every report in the Workday and termination folders
    python update_employees.py --backfill-terminated   # optional: add people only found in termination reports
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database.staffing_db import connect, replace_snapshot, upsert_staffing, _clean_id  # noqa: E402

WORKDAY_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/"
TERMINATION_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Termination Reports"

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


def _last_segment(series: pd.Series) -> pd.Series:
    """'Terminate Employee > Voluntary' -> 'Voluntary' (keeps the final '>' segment)."""
    s = series.astype("string").str.strip()
    return s.str.split(">").str[-1].str.strip().mask(lambda x: x == "")


def prepare_terminations(df: pd.DataFrame) -> pd.DataFrame:
    out = _select(df, TERMINATION_COLS)
    out["fte"] = pd.NA
    out["termination_category"] = _last_segment(out["termination_category"])
    out["termination_reason"] = _last_segment(out["termination_reason"])
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
    if pd.isna(v):
        return None
    return v.item() if hasattr(v, "item") else v


def apply_current_workers(conn, current: pd.DataFrame, report_date: str) -> int:
    """Upsert everyone on the current worker report. A prior termination date is
    cleared only when the person has been rehired (hire date after termination)."""
    sql = """
    INSERT INTO employees (employee_id, employee_type, last_name, first_name, full_name, hire_date)
    VALUES (?,?,?,?,?,?)
    ON CONFLICT(employee_id) DO UPDATE SET
        employee_type=excluded.employee_type,
        last_name=excluded.last_name, first_name=excluded.first_name,
        full_name=excluded.full_name, hire_date=excluded.hire_date,
        termination_category=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_category END,
        termination_reason=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_reason END,
        termination_date=CASE WHEN excluded.hire_date > employees.termination_date
            THEN NULL ELSE employees.termination_date END
    """
    rows = [
        tuple(_val(r[c]) for c in ("employee_id", "employee_type", "last_name", "first_name",
                                   "full_name", "hire_date"))
        for _, r in current.iterrows()
    ]
    conn.executemany(sql, rows)
    return len(rows)


def apply_terminations(conn, terms: pd.DataFrame, insert_unknown=True) -> tuple:
    """Set termination data by employee ID. Unknown IDs are inserted as terminated
    employees (with a blank employee_type if it can't be determined) unless
    insert_unknown is False. Returns (updated, inserted)."""
    updated = inserted = 0
    for _, r in terms.iterrows():
        eid = int(r["employee_id"])
        cur = conn.execute(
            """UPDATE employees SET termination_date=?, termination_category=?,
               termination_reason=? WHERE employee_id=?""",
            (_val(r["termination_date"]), _val(r["termination_category"]),
             _val(r["termination_reason"]), eid),
        )
        if cur.rowcount:
            updated += 1
        elif not insert_unknown:
            continue
        else:
            conn.execute(
                """INSERT INTO employees (employee_id, employee_type, last_name, first_name,
                   full_name, hire_date, termination_date, termination_category,
                   termination_reason)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                tuple(_val(r[c]) for c in ("employee_id", "employee_type", "last_name",
                      "first_name", "full_name", "hire_date", "termination_date",
                      "termination_category", "termination_reason")),
            )
            inserted += 1
    return updated, inserted


def record_snapshot(conn, current: pd.DataFrame, report_date: str, tsm=None, db_path=None) -> int:
    """Store the roster on the report (excluding anyone terminated by the report date) as
    snapshot rows. CDL details come from the optional training master and live only in snapshots."""
    roster = current[["employee_id", "employee_type", "last_name", "first_name",
                      "full_name", "hire_date"]].copy()
    term = pd.read_sql_query("SELECT employee_id, termination_date FROM employees", conn)
    roster = roster.merge(term, on="employee_id", how="left")
    roster = roster[roster["termination_date"].isna() | (roster["termination_date"] > report_date)]
    roster = roster.drop(columns="termination_date")
    if roster.empty:
        return 0
    tsm_cols = ["driver_num", "active", "permit", "cdl", "cdl_training_start_date"]
    if tsm is not None:
        roster = roster.merge(tsm, on="employee_id", how="left")
    else:
        for c in tsm_cols:
            roster[c] = pd.NA
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
    # snapshot rows go in separate transaction(s) after employees are committed
    with connect(db_path) as conn:
        n_snap = record_snapshot(conn, current, report_date, tsm, db_path)
    return {"current_workers": n_current, "terminations_updated": updated,
            "terminations_inserted": inserted, "snapshot_rows": n_snap}


def _report_date_from_name(path) -> str:
    """Extract the MM_DD_YYYY (or MM-DD-YYYY / YYYY-MM-DD) date embedded in a report file name."""
    name = Path(path).stem
    m = re.search(r"(\d{1,2})[_-](\d{1,2})[_-](\d{4})", name)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{4})[_-](\d{1,2})[_-](\d{1,2})", name)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    raise ValueError(f"Could not find a date in report file name: {name}")


def _list_reports(folder, require_date=True) -> list:
    """Excel reports in a folder, oldest first (by file-name date, else modified time)."""
    files = [p for p in Path(folder).glob("*.xlsx") if not p.name.startswith("~$")]

    def key(p):
        try:
            return (_report_date_from_name(p), p.name)
        except ValueError:
            if require_date:
                raise
            return (pd.Timestamp(p.stat().st_mtime, unit="s").strftime("%Y-%m-%d"), p.name)

    return sorted(files, key=key)


def backfill_staffing_database(workday_folder=WORKDAY_REPORT_PATH,
                               termination_folder=TERMINATION_REPORT_PATH,
                               db_path=None) -> dict:
    """Populate the database from every Workday report and termination report in the folders.

    Workday reports are processed oldest to newest (dates come from the file names), each
    upserting employees and recording that day's snapshot. Termination reports are then
    applied oldest to newest. Employees are keyed by employee ID, so the run is idempotent.
    A report that fails is reported and skipped so one bad file doesn't stop the backfill.
    """
    summary = {"workday_reports": 0, "termination_reports": 0, "current_workers": 0,
               "snapshot_rows": 0, "terminations_updated": 0, "terminations_inserted": 0,
               "failed": []}

    for path in _list_reports(workday_folder):
        try:
            report_date = _report_date_from_name(path)
            current = prepare_current(read_report(path))
            with connect(db_path) as conn:
                summary["current_workers"] += apply_current_workers(conn, current, report_date)
            with connect(db_path) as conn:
                summary["snapshot_rows"] += record_snapshot(conn, current, report_date, db_path=db_path)
            summary["workday_reports"] += 1
        except Exception as exc:
            print(f"Failed workday report {path.name}: {exc}")
            summary["failed"].append(str(path))

    for path in _list_reports(termination_folder, require_date=False):
        try:
            terms = prepare_terminations(read_report(path))
            with connect(db_path) as conn:
                updated, inserted = apply_terminations(conn, terms, insert_unknown=False)
            summary["terminations_updated"] += updated
            summary["terminations_inserted"] += inserted
            summary["termination_reports"] += 1
        except Exception as exc:
            print(f"Failed termination report {path.name}: {exc}")
            summary["failed"].append(str(path))

    return summary


def backfill_terminated_employees(termination_folder=TERMINATION_REPORT_PATH, db_path=None) -> dict:
    """Optional: add people from the termination reports who never appear on a Workday report.

    Anyone in a termination report whose ID is not yet in `employees` (they left before the
    earliest current worker report) is inserted with their termination details. They are also
    added to every existing snapshot date between their hire date (inclusive) and termination
    date (exclusive), so historical trend counts include them. People whose employee type can't
    be determined are stored with a blank type and left out of snapshots (which are keyed by type).
    Run it after
    backfill_staffing_database so the snapshot dates already exist. Idempotent.
    """
    summary = {"termination_reports": 0, "employees_added": 0, "snapshot_rows": 0, "failed": []}
    new_ids = set()

    for path in _list_reports(termination_folder, require_date=False):
        try:
            terms = prepare_terminations(read_report(path))
            with connect(db_path) as conn:
                known = {r[0] for r in conn.execute("SELECT employee_id FROM employees")}
                unknown = terms[~terms["employee_id"].isin(known)]
                _, inserted = apply_terminations(conn, unknown)
            new_ids.update(int(i) for i in unknown["employee_id"])
            summary["employees_added"] += inserted
            summary["termination_reports"] += 1
        except Exception as exc:
            print(f"Failed termination report {path.name}: {exc}")
            summary["failed"].append(str(path))

    if not new_ids:
        return summary

    with connect(db_path) as conn:
        marks = ",".join("?" * len(new_ids))
        people = pd.read_sql_query(
            f"""SELECT employee_id, employee_type, last_name, first_name, full_name, hire_date,
                       termination_date FROM employees WHERE employee_id IN ({marks})""",
            conn, params=sorted(new_ids))
        dates = [r[0] for r in conn.execute("SELECT DISTINCT snapshot_date FROM staffing_snapshots")]

    frames = []
    for d in dates:
        active = people[(people["hire_date"] <= d) & (people["termination_date"] > d)].copy()
        if not active.empty:
            active["date"] = d
            frames.append(active)
    if frames:
        rows = pd.concat(frames).drop(columns="termination_date")
        rows = rows[rows["employee_type"].notna()]  # snapshots are keyed by type
        rows["cdl_status"] = rows["employee_type"].map(
            lambda t: "unknown" if t == "student" else "not-applicable")
        for emp_type, grp in rows.groupby("employee_type"):
            summary["snapshot_rows"] += upsert_staffing(grp, emp_type, db_path=db_path)
    return summary


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--backfill-terminated":
        print(backfill_terminated_employees())
        sys.exit(0)
    if len(sys.argv) == 2 and sys.argv[1] == "--backfill":
        print(backfill_staffing_database())
        sys.exit(0)
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    print(update_staffing_database(sys.argv[1], sys.argv[2], sys.argv[3],
                                   sys.argv[4] if len(sys.argv) > 4 else None))
