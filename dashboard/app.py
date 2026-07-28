import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date

from shiny.express import ui, render, input
from shiny import reactive
from faicons import icon_svg

pd.set_option("display.max_columns", None)

# ----------------------------------------------------------------------------------
# Staffing data import
# ----------------------------------------------------------------------------------

# import
try:
    from shared import df
except ImportError:
    print("Fail")

# print(df)
staffing_df = df.copy()

# ----------------------------------------------------------------------------------
# Options and navbar
# ----------------------------------------------------------------------------------
ui.page_opts(
    fillable=True,
)

# Remove default body margin so navbar sits flush at the top
ui.tags.style("body { margin: 0; padding: 0; } .bslib-page-fill { padding: 0; }")

# 2. navset_bar as top-level nav with title
with ui.navset_bar(
    id="page_tabs",
    title=ui.span(
        icon_svg("van-shuttle"),
        " TTM Dashboard"
    ),
    navbar_options=ui.navbar_options(
        bg="#090949",
        theme="dark"
    )
):
    # ----------------------------------------------------------------------------------
    # Page 1: Staffing
    # NOTE: Add trend once we have another set of data here
    # ----------------------------------------------------------------------------------
    with ui.nav_panel("Staffing", icon=icon_svg("users")):
        # Sidebar inside the nav panel
        with ui.layout_sidebar():
            with ui.sidebar(width=270, open="desktop"):
                ui.h5("Employee Filters", style="margin-top: 0;")

                ui.input_date_range(
                    "date_range",
                    "Snapshot Date Range",
                    start=str(staffing_df['date'].min().date()),
                    end=str(staffing_df['date'].max().date()),
                    min=str(staffing_df['date'].min().date()),
                    max=str(staffing_df['date'].max().date()),
                )

                ui.hr()
                ui.input_checkbox_group(
                    "emp_types",
                    "Employee Type",
                    choices={"full_time": "Full Time", "part_time": "Part Time", "student": "Student"},
                    selected=["full_time", "part_time", "student"],
                )

            # --- Reactive filtered dataframe ---
            # Filters to the snapshot window using the 'date' column (snapshot date),
            # not hire_date. Each row's 'date' = the date that batch was recorded.
            @reactive.calc
            def filtered_df():
                start = pd.to_datetime(input.date_range()[0])
                end = pd.to_datetime(input.date_range()[1])
                types = input.emp_types()
                df_f = staffing_df[
                    (staffing_df['date'] >= start) &
                    (staffing_df['date'] <= end) &
                    (staffing_df['employee_type'].isin(types))
                ]
                return df_f

            # Top 4 KPI value boxes
            with ui.layout_column_wrap(fill=False):

                # 1) total headcount
                with ui.value_box(showcase=icon_svg("users")):
                    "Total Headcount"
                    @render.text
                    def count():
                        return f"{filtered_df().shape[0]} Employees"

                # 2) full time headcount
                with ui.value_box(showcase=icon_svg("clock")):
                    "Full Time"
                    @render.text
                    def full_time_count():
                        return f"{filtered_df()[filtered_df()['employee_type'] == 'full_time'].shape[0]} Employees"

                # 3) part time headcount
                with ui.value_box(showcase=icon_svg("user-clock")):
                    "Part Time"
                    @render.text
                    def part_time_count():
                        return f"{filtered_df()[filtered_df()['employee_type'] == 'part_time'].shape[0]} Employees"

                # 4) students headcount
                with ui.value_box(showcase=icon_svg("graduation-cap")):
                    "Students"
                    @render.text
                    def student_count():
                        return f"{filtered_df()[filtered_df()['employee_type'] == 'student'].shape[0]} Employees"


            # --- Charts row ---
            with ui.layout_column_wrap(width="25%"):

                # Staffing trend over time
                with ui.card():
                    ui.card_header("Staffing Trend")

                # Student employee type donut chart
                with ui.card():
                    ui.card_header("Student Employee Breakdown")
                

    # ----------------------------------------------------------------------------------
    # Page 2: Ridership
    # ----------------------------------------------------------------------------------
    with ui.nav_panel("Ridership", icon=icon_svg("chart-line")):
        with ui.layout_sidebar():
            with ui.sidebar(width=250, open="desktop"):
                ui.h5("Filters", style="margin-top: 0;")
                ui.input_select("route", "Select Route", choices=["All", "Buckeye Express (BE)", "Campus Connector (CC)"])
            ui.p("Under Construction")



    # ----------------------------------------------------------------------------------
    # Page 3: Future Expansion????
    # ----------------------------------------------------------------------------------
    with ui.nav_menu("Reports", icon=icon_svg("file-lines")):
        with ui.nav_panel("Financial Breakdown"):
            ui.p("Under Construction")
        with ui.nav_panel("On-Demand Breakdown"):
            ui.p("Under Construction")
        with ui.nav_panel("Charter Breakdown"):
            ui.p("Under Construction")


    # ----------------------------------------------------------------------------------
    # Link documentation to source code on the side here
    # ----------------------------------------------------------------------------------
    ui.nav_spacer()

    with ui.nav_control():
        ui.a(
            icon_svg("git-alt"), " Docs",
            href="https://code.osu.edu/morgan.1461/ttm-dashboard",
            target="_blank",
            class_="nav-link"
        )
