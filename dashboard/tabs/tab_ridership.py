from shiny.express import module, ui
from faicons import icon_svg


@module
def ridership_tab(input, output, session):
    with ui.nav_panel("Ridership", icon=icon_svg("chart-line")):
        ui.p("Under Construction")
