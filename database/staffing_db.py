"""Local SQLite backend for staffing snapshot data.

One row per (snapshot_date, employee_type, employee_id). Writes are idempotent
upserts, so re-running a load for the same date never creates duplicates.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ttm_dashboard.db"
DB_PATH = Path(os.environ.get("TTM_DB_PATH", DEFAULT_DB_PATH))

EMPLOYEE_TYPES = {"full_time", "part_time", "student"}

# column -> SQL type (besides the key columns)
VALUE_COLUMNS = {
    "full_name": "TEXT",
    "last_name": "TEXT",
    "first_name": "TEXT",
    "hire_date": "TEXT",
    "cdl_status": "TEXT",
    "driver_num": "REAL",
    "active": "REAL",
    "permit": "REAL",
    "cdl": "REAL",
    "cdl_training_start_date": "TEXT",
}
KEY_COLUMNS = ["snapshot_date", "employee_type", "employee_id"]
DATE_COLUMNS = ["hire_date", "cdl_training_start_date"]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS staffing_snapshots (
    snapshot_date TEXT NOT NULL,
    employee_type TEXT NOT NULL CHECK (employee_type IN ('full_time','part_time','student')),
    employee_id   TEXT NOT NULL,
    {', '.join(f'{c} {t}' for c, t in VALUE_COLUMNS.items())},
    loaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (snapshot_date, employee_type, employee_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_staffing_date ON staffing_snapshots (snapshot_date);
"""


@contextmanager
def connect(db_path=None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _clean_id(series: pd.Series) -> pd.Series:
    ids = series.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
    return ids.mask(ids == "")


def _prepare(df: pd.DataFrame, employee_type=None) -> pd.DataFrame:
    """Normalize a staffing frame to the table layout, dropping duplicates."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    id_col = next((c for c in ("employee_id", "ID", "id") if c in out.columns), None)
    if id_col is None:
        raise ValueError("Staffing data needs an 'ID' (or 'id'/'employee_id') column.")
    out["employee_id"] = _clean_id(out[id_col])
    if employee_type is not None:
        out["employee_type"] = employee_type
    if "employee_type" not in out.columns:
        raise ValueError("employee_type is required.")
    bad = set(out["employee_type"].dropna().unique()) - EMPLOYEE_TYPES
    if bad:
        raise ValueError(f"Unknown employee_type values: {sorted(bad)}")
    if "date" in out.columns:
        out["snapshot_date"] = pd.to_datetime(out["date"], errors="coerce")
    elif "snapshot_date" in out.columns:
        out["snapshot_date"] = pd.to_datetime(out["snapshot_date"], errors="coerce")
    else:
        raise ValueError("A 'date' column is required.")

    missing = out[KEY_COLUMNS].isna().any(axis=1)
    if missing.any():
        print(f"Warning: dropping {int(missing.sum())} rows missing id/date/type.")
        out = out[~missing]

    out["snapshot_date"] = out["snapshot_date"].dt.strftime("%Y-%m-%d")
    for c in VALUE_COLUMNS:
        if c not in out.columns:
            out[c] = None
    for c in DATE_COLUMNS:
        out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%Y-%m-%d")
    for c, t in VALUE_COLUMNS.items():
        if t == "REAL":
            out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out[KEY_COLUMNS + list(VALUE_COLUMNS)]
    return out.drop_duplicates(subset=KEY_COLUMNS, keep="last")


def _write(conn, rows: pd.DataFrame) -> int:
    cols = KEY_COLUMNS + list(VALUE_COLUMNS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in VALUE_COLUMNS)
    sql = (
        f"INSERT INTO staffing_snapshots ({', '.join(cols)}) "
        f"VALUES ({', '.join('?' * len(cols))}) "
        f"ON CONFLICT({', '.join(KEY_COLUMNS)}) DO UPDATE SET {updates}, loaded_at=datetime('now')"
    )
    records = [
        tuple(None if pd.isna(v) else v for v in r)
        for r in rows.itertuples(index=False, name=None)
    ]
    conn.executemany(sql, records)
    return len(records)


def upsert_staffing(df: pd.DataFrame, employee_type=None, db_path=None) -> int:
    """Insert or update snapshot rows. Returns the number of rows written."""
    rows = _prepare(df, employee_type)
    if rows.empty:
        return 0
    with connect(db_path) as conn:
        return _write(conn, rows)


def replace_snapshot(df: pd.DataFrame, employee_type: str, snapshot_date, db_path=None) -> int:
    """Atomically replace one (date, type) snapshot so people removed from a
    re-run report do not linger."""
    date_str = pd.to_datetime(snapshot_date).strftime("%Y-%m-%d")
    rows = _prepare(df, employee_type)
    if not rows.empty:
        rows = rows[rows["snapshot_date"] == date_str]
    with connect(db_path) as conn:
        conn.execute(
            "DELETE FROM staffing_snapshots WHERE snapshot_date=? AND employee_type=?",
            (date_str, employee_type),
        )
        return _write(conn, rows) if not rows.empty else 0


def load_staffing(db_path=None) -> pd.DataFrame:
    """Return all staffing rows in the shape the dashboard expects."""
    with connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM staffing_snapshots ORDER BY snapshot_date, employee_type, employee_id",
            conn,
        )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["snapshot_date"])
    for c in DATE_COLUMNS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["ID"] = df["employee_id"]
    return df.drop(columns=["snapshot_date", "loaded_at"])
