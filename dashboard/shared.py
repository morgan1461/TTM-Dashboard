import re
from pathlib import Path
import pandas as pd

DATA_REPO = Path("K:/AP/TTM/Data/+ Data Repository/Dashboard/")
STAFFING_DATA_DIR = DATA_REPO / "Staffing" / "dashboard_data"

FULL_TIME_DIR = STAFFING_DATA_DIR / "full_time"
PART_TIME_DIR = STAFFING_DATA_DIR / "part_time"
STUDENT_DIR = STAFFING_DATA_DIR / "student"

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".parquet", ".feather"}


def _read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    try:
        if suffix in {".csv", ".tsv"}:
            sep = "\t" if suffix == ".tsv" else ","
            return pd.read_csv(path, sep=sep)
        if suffix in {".xlsx", ".xls", ".xlsm"}:
            return pd.read_excel(path)
        if suffix == ".parquet":
            return pd.read_parquet(path)
        if suffix == ".feather":
            return pd.read_feather(path)
    except Exception as err:
        print(f"Warning: Skipping file '{path.name}' due to read error: {err}")
        return pd.DataFrame()

    return pd.DataFrame()


def _extract_snapshot_date(path: Path) -> pd.Timestamp:
    """
    Searches for any date format in the filename stem.
    If no date exists in the filename, falls back to the file's modification date.
    """
    patterns = [
        r"\b\d{4}[-_/]\d{1,2}[-_/]\d{1,2}\b",  # 2024-01-15 or 2024/1/15
        r"\b\d{1,2}[-_/]\d{1,2}[-_/]\d{4}\b",  # 01-15-2024 or 1/15/2024
        r"\b20\d{6}\b"                          # 20240115
    ]

    for pattern in patterns:
        match = re.search(pattern, path.stem)
        if match:
            parsed = pd.to_datetime(match.group(0), errors="coerce")
            if pd.notna(parsed):
                return parsed

    # Fallback to file creation / last modified timestamp
    return pd.to_datetime(path.stat().st_mtime, unit="s")


def _normalize_staffing_frame(frame: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    if frame.empty:
        return frame

    normalized = frame.copy()

    # Drop Unnamed index artifact columns
    normalized = normalized.loc[:, ~normalized.columns.astype(str).str.startswith("Unnamed")]

    # Rename standard Workday variations
    rename_map = {
        "full_name_workday": "full_name",
        "hire_date_workday": "hire_date",
    }
    normalized = normalized.rename(columns=rename_map)

    # Cross-fill type and status if one is missing
    if "employee_type" not in normalized.columns and "employee_status" in normalized.columns:
        normalized["employee_type"] = normalized["employee_status"]
    elif "employee_status" not in normalized.columns and "employee_type" in normalized.columns:
        normalized["employee_status"] = normalized["employee_type"]

    # Assign dates
    snapshot_date = _extract_snapshot_date(source_file)
    if "date" in normalized.columns:
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").fillna(snapshot_date)
    else:
        normalized["date"] = snapshot_date

    normalized["source_file"] = source_file.name

    # Column defaults
    normalized["cdl_status"] = normalized.get("cdl_status", pd.Series(dtype=object)).fillna("not-applicable")

    if "full_name" not in normalized.columns:
        normalized["full_name"] = pd.NA

    if "hire_date" in normalized.columns:
        normalized["hire_date"] = pd.to_datetime(normalized["hire_date"], errors="coerce")

    return normalized


def load_directory(directory: Path) -> pd.DataFrame:
    if not directory.exists():
        return pd.DataFrame()

    # Get all files regardless of naming structure, ignoring temp/hidden files
    files = sorted([
        f for f in directory.iterdir()
        if f.is_file()
        and not f.name.startswith("~")
        and not f.name.startswith(".")
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not files:
        return pd.DataFrame()

    frames = []
    for file_path in files:
        frame = _read_file(file_path)
        if not frame.empty:
            frames.append(_normalize_staffing_frame(frame, file_path))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# Load individual directories
full_time_df = load_directory(FULL_TIME_DIR)
full_time_df['employee_type'] = 'full_time'  # Ensure employee_type is set for full-time data
part_time_df = load_directory(PART_TIME_DIR)
part_time_df['employee_type'] = 'part_time'  # Ensure employee_type is set for part-time data
student_df = load_directory(STUDENT_DIR)
student_df['employee_type'] = 'student'  # Ensure employee_type is set for student data

# Combined dataset for dashboard app
df = pd.concat([full_time_df, part_time_df, student_df], ignore_index=True)