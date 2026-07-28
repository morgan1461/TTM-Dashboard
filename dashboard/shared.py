from pathlib import Path

import pandas as pd

app_dir = Path(__file__).parent

DATA_REPO = Path("K:/AP/TTM/Data/+ Data Repository/Dashboard/")
STAFFING_DATA_DIR = DATA_REPO / "Staffing" / "dashboard_data"

FULL_TIME_DIR = STAFFING_DATA_DIR / "full_time"
PART_TIME_DIR = STAFFING_DATA_DIR / "part_time"
STUDENT_DIR = STAFFING_DATA_DIR / "student"

SUPPORTED_EXTENSIONS = ("*.csv", "*.xlsx", "*.xls", "*.parquet")


def _read_file(path: Path) -> pd.DataFrame:
	suffix = path.suffix.lower()
	if suffix == ".csv":
		return pd.read_csv(path)
	if suffix in {".xlsx", ".xls"}:
		return pd.read_excel(path)
	if suffix == ".parquet":
		return pd.read_parquet(path)
	raise ValueError(f"Unsupported file type: {path.suffix}")


def _extract_snapshot_date(path: Path) -> pd.Timestamp:
	return pd.to_datetime(path.stem[:10], errors="coerce")


def _normalize_staffing_frame(frame: pd.DataFrame, source_file: Path) -> pd.DataFrame:
	normalized = frame.copy()
	normalized = normalized.loc[:, ~normalized.columns.astype(str).str.startswith("Unnamed")]

	rename_map = {
		"full_name_workday": "full_name",
		"hire_date_workday": "hire_date",
	}
	normalized = normalized.rename(columns=rename_map)

	if "employee_type" not in normalized.columns and "employee_status" in normalized.columns:
		normalized["employee_type"] = normalized["employee_status"]
	if "employee_status" not in normalized.columns and "employee_type" in normalized.columns:
		normalized["employee_status"] = normalized["employee_type"]

	normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce") if "date" in normalized.columns else pd.NaT
	snapshot_date = _extract_snapshot_date(source_file)
	normalized["date"] = normalized["date"].fillna(snapshot_date)
	normalized["source_file"] = source_file.name

	if "cdl_status" not in normalized.columns:
		normalized["cdl_status"] = "not-applicable"
	else:
		normalized["cdl_status"] = normalized["cdl_status"].fillna("not-applicable")

	if "full_name" not in normalized.columns:
		normalized["full_name"] = pd.NA

	if "hire_date" in normalized.columns:
		normalized["hire_date"] = pd.to_datetime(normalized["hire_date"], errors="coerce")

	return normalized


def _load_directory(directory: Path) -> pd.DataFrame:
	files = []
	for pattern in SUPPORTED_EXTENSIONS:
		files.extend(directory.glob(pattern))

	files = sorted(files)
	if not files:
		return pd.DataFrame()

	frames = []
	for file_path in files:
		frame = _read_file(file_path)
		frames.append(_normalize_staffing_frame(frame, file_path))

	return pd.concat(frames, ignore_index=True)


full_time_df = _load_directory(FULL_TIME_DIR)
part_time_df = _load_directory(PART_TIME_DIR)
student_df = _load_directory(STUDENT_DIR)

# Combined dataset used by dashboard app.
df = pd.concat([full_time_df, part_time_df, student_df], ignore_index=True)
