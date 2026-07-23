import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from faicons import icon_svg

from shiny import reactive
from shiny.express import input, render, ui

# ------------------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------------------

def format_trend_html(diff_val):
    """Formats numeric change into colored HTML with direction arrows."""
    if pd.isna(diff_val) or diff_val == 0:
        return "<span style='color: #7f8c8d; font-size: 0.95rem; font-weight: bold;'>▬ 0 (No change)</span>"
    elif diff_val > 0:
        return f"<span style='color: #27ae60; font-size: 0.95rem; font-weight: bold;'>▲ +{int(diff_val)} gained</span>"
    else:
        return f"<span style='color: #e74c3c; font-size: 0.95rem; font-weight: bold;'>▼ {int(diff_val)} lost</span>"

# ------------------------------------------------------------------------------------------
# Options and sidebar filters - GLOBAL
# ------------------------------------------------------------------------------------------
ui.page_opts(
    title=ui.TagList(
        icon_svg("bus"), " ",
        "TTM Dashboard"
    ),
    window_title="TTM Dashboard",
    fillable=True,
    bg='#00274c',
    inverse=True
)

# Need multiple data import here, one per each tab
try:
    from shared import app_dir, df
except ImportError:
    import pathlib
    app_dir = pathlib.Path(__file__).parent if "__file__" in locals() else pathlib.Path(".")
    df = pd.read_csv("test_data.csv")

# Ensure proper datetime parsing for date filtering
df["date"] = pd.to_datetime(df["date"])
available_dates = sorted(df["date"].dt.strftime("%Y-%m-%d").unique())

with ui.sidebar(title="Filter controls"):
    ui.input_select(
        "selected_date",
        "Reporting Date",
        choices=available_dates,
        selected=available_dates[-1] if available_dates else None,
    )
    ui.input_checkbox_group(
        "emp_status",
        "Employee Status",
        ["Full Time", "Part Time", "Student"],
        selected=["Full Time", "Part Time", "Student"],
    )
    ui.input_checkbox_group(
        "cdl_status",
        "CDL Status",
        ["CDL", "Non-CDL", "Training"],
        selected=["CDL", "Non-CDL", "Training"],
    )

# ----------------------------------------------------------------------------------------------
# Staffing Dashboard Page
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("Staffing"):

    # Top 4 KPI values of staffing numbers total, ft, pt, student
    with ui.layout_column_wrap(fill=False):

        # 1. Total Headcount:
        with ui.value_box(showcase=icon_svg("users")):
            # Title
            "Total Headcount"

            # KPI Value
            @render.text 
            def count():
                return f"{filtered_df().shape[0]} Employees"

            # Trend Indicator
            @render.text
            def trend():
                # Get the current and previous date for comparison
                current_date = pd.to_datetime(input.selected_date())
                previous_date = current_date - pd.DateOffset(months=1)

                # Filter the dataframe for the current and previous dates
                current_count = df[df["date"] == current_date].shape[0]
                previous_count = df[df["date"] == previous_date].shape[0]

                # Calculate the difference
                diff_val = current_count - previous_count

                # Format the trend indicator
                return format_trend_html(diff_val)

        # 2. Full Time Employees:
        with ui.value_box(showcase=icon_svg("users")):
            "Full Time Employees"

            @render.text
            def full_time_count():
                total_full_time = filtered_df()[filtered_df()["employee_status"] == "Full Time"].shape[0]
                return f"{total_full_time} Employees"

        # 3. Part Time Employees:
        with ui.value_box(showcase=icon_svg("graduation-cap")):
            "Part Time Employees"

            @render.text
            def part_time_count():
                total_part_time = filtered_df()[filtered_df()["employee_status"] == "Part Time"].shape[0]
                return f"{total_part_time} Part Time"

        # 4. Student Employees:
        with ui.value_box(showcase=icon_svg("graduation-cap")):
            "Student Employees"

            @render.text
            def student_count():
                total_students = filtered_df()[filtered_df()["employee_status"] == "Student"].shape[0]
                return f"{total_students} Students"



    # Charts and full searchable data table
    with ui.layout_columns():
        with ui.card(full_screen=True):
            ui.card_header("Staffing Breakdown by Category")

            @render.plot
            def staffing_breakdown():
                f_df = filtered_df()
                if f_df.empty:
                    fig, ax = plt.subplots()
                    ax.text(0.5, 0.5, "No data available for filters", ha="center", va="center")
                    return fig
                
                # Group by Employee Status and CDL Status
                counts = f_df.groupby(["employee_status", "cdl_status"]).size().reset_index(name="count")
                
                fig, ax = plt.subplots(figsize=(8, 5))
                sns.barplot(
                    data=counts,
                    x="employee_status",
                    y="count",
                    hue="cdl_status",
                    palette="Set2",
                    ax=ax
                )
                ax.set_title("Employee Count by Employment and CDL Status")
                ax.set_xlabel("Employee Status")
                ax.set_ylabel("Headcount")
                ax.legend(title="CDL Status")
                plt.tight_layout()
                return fig

        with ui.card(full_screen=True):
            ui.card_header("Employee Records Table")

            @render.data_frame
            def summary_statistics():
                cols = [
                    "name",
                    "employee_status",
                    "cdl_status",
                    "hire_date",
                    "date",
                ]
                display_df = filtered_df()[cols].copy()
                display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
                return render.DataGrid(display_df, filters=True)

    # Include optional external CSS stylesheet
    if (app_dir / "styles.css").exists():
        ui.include_css(app_dir / "styles.css")




    # reactive filter calculation
    @reactive.calc
    def filtered_df():
        filt_df = df.copy()
        
        # Date Filter
        if input.selected_date():
            sel_dt = pd.to_datetime(input.selected_date())
            filt_df = filt_df[filt_df["date"] == sel_dt]
            
        # Employee Status Filter
        filt_df = filt_df[filt_df["employee_status"].isin(input.emp_status())]
        
        # CDL Status Filter
        filt_df = filt_df[filt_df["cdl_status"].isin(input.cdl_status())]
        
        return filt_df




# ----------------------------------------------------------------------------------------------
# Potential INTERNAL med center express dashboard page?
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("Med Center Express (MC)"):
    ui.h2("Med Center Express Dashboard")
    ui.p("Concept dashboard.")

# ----------------------------------------------------------------------------------------------
# Maybe one page dashboard per route?
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("Campus Connector (CC)"):
    ui.h2("Campus Connector (CC) Dashboard")
    ui.p("Concept dashboard.")

# ----------------------------------------------------------------------------------------------
# Maybe one page dashboard per route?
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("Buckeye Express (BE)"):
    ui.h2("Buckeye Express (BE) Dashboard")
    ui.p("Concept dashboard.")

# ----------------------------------------------------------------------------------------------
# Potential On Demand dashboard page?
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("On Demand"):
    ui.h2("On Demand Dashboard")
    ui.p("Concept dashboard.")

# ----------------------------------------------------------------------------------------------
# Potential On Demand dashboard page?
# ----------------------------------------------------------------------------------------------
with ui.nav_panel("Driver Facing"):
    ui.h2("Copy of the public Driver Facing Dashboard")
    ui.p("Concept dashboard.")