from shiny.express import ui, render
from faicons import icon_svg

# 1. Configure page options
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
    # ----------------------------------------------------------------------------------
    with ui.nav_panel("Staffing", icon=icon_svg("users")):
        # Sidebar inside the nav panel
        with ui.layout_sidebar():
            with ui.sidebar(width=250, open="desktop"):
                ui.h5("Employee Filters", style="margin-top: 0;")
                ui.input_select("employee_type", "Select Type", choices=["Full Time", "Part Time", "Student"])

            
            ui.h2("Staffing")
            ui.p("Under Construction")






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
