import pandas as pd
from pathlib import Path

from shiny.express import ui
from faicons import icon_svg

from colors import NAVBAR_COLOR
from tabs.tab_staffing import staffing_tab
from tabs.tab_student_trends import student_trends_tab
from tabs.tab_ridership import ridership_tab

pd.set_option("display.max_columns", None)

# ----------------------------------------------------------------------------------
#  data import
# ----------------------------------------------------------------------------------
# staffing data
try:
    from shared import staffing_df
except ImportError:
    print("Fail: Staffing data not found")

staffing_df = staffing_df.copy()

# student trends data
try:
    from shared import student_trends_df
except ImportError:
    print("Fail: Student trends data not found")

student_trends_df = student_trends_df.copy()

# ----------------------------------------------------------------------------------
# Options and navbar
# ----------------------------------------------------------------------------------
ui.page_opts(
    fillable=True,
)

ui.include_css(Path(__file__).parent / "styles.css")

with ui.navset_bar(
    id="page_tabs",
    title=ui.span(
        icon_svg("van-shuttle"),
        " TTM Dashboard"
    ),
    navbar_options=ui.navbar_options(
        bg=NAVBAR_COLOR,
        theme="dark"
    )
):
    staffing_tab("staffing", staffing_df)
    student_trends_tab("student_trends", student_trends_df)
    ridership_tab("ridership")

    # ----------------------------------------------------------------------------------
    # Page X: Reports
    # ----------------------------------------------------------------------------------
    # with ui.nav_menu("Reports", icon=icon_svg("file-lines")):
    #     with ui.nav_panel("Financial Breakdown"):
    #         ui.p("Concept")
    #     with ui.nav_panel("On-Demand Breakdown"):
    #         ui.p("Concept")
    #     with ui.nav_panel("Charter Breakdown"):
    #         ui.p("Concept")

    # ----------------------------------------------------------------------------------
    # End of the nav bar
    # ----------------------------------------------------------------------------------

    ui.nav_spacer()

    with ui.nav_control():
        with ui.tooltip(placement="bottom"):
            ui.tags.button(
                icon_svg("circle-info"),
                " About",
                class_="nav-link",
                style="display: inline-flex; align-items: center; gap: 6px; color: #F8FAFC !important; border: none; text-decoration: none; padding: 0.5rem;",
            )
            "Developed by Clay Morgan for The Ohio State University Transportation and Traffic Management. Please reach out to Morgan.1461@osu.edu if errors or problems are found."

    with ui.nav_control():
        ui.a(
            icon_svg("git-alt"), " Docs",
            href="https://code.osu.edu/morgan.1461/ttm-dashboard",
            target="_blank",
            class_="nav-link"
        )
