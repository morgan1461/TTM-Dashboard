import pandas as pd
from shiny.express import ui


def _clean_name_series(name_series: pd.Series) -> pd.Series:
    cleaned = name_series.dropna().astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    return cleaned


def _name_delta(previous_df: pd.DataFrame, current_df: pd.DataFrame) -> tuple[list[str], list[str]]:
    previous_names = set(_clean_name_series(previous_df.get("full_name", pd.Series(dtype=object))).tolist())
    current_names = set(_clean_name_series(current_df.get("full_name", pd.Series(dtype=object))).tolist())

    gained = sorted(current_names - previous_names)
    lost = sorted(previous_names - current_names)
    return gained, lost


def _kpi_summary_ui(current: int, trend: int, gained_count: int, lost_count: int):
    trend_class = "kpi-pill kpi-pill-flat"
    if trend > 0:
        trend_class = "kpi-pill kpi-pill-up"
    elif trend < 0:
        trend_class = "kpi-pill kpi-pill-down"

    return ui.tags.div(
        ui.tags.div(
            ui.tags.span(str(current), class_="kpi-current"),
            ui.tags.span(f"{trend:+}", class_=trend_class),
            class_="kpi-main-row",
        ),
        ui.tags.div(
            ui.tags.span(f"+{gained_count} gained", class_="kpi-pill kpi-pill-up-soft"),
            ui.tags.span(f"-{lost_count} lost", class_="kpi-pill kpi-pill-down-soft"),
            class_="kpi-sub-row",
        ),
        class_="kpi-stack",
    )
