import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date
import plotly.graph_objects as go

from shiny.express import ui, render, input
from shiny import reactive
from faicons import icon_svg
from shinywidgets import render_widget

pd.set_option("display.max_columns", None)

NAVBAR_COLOR = "#090949"
FT_COLOR = "#023047"
PT_COLOR = "#219ebc"
STUDENT_COLOR = "#8ecae6"

# ----------------------------------------------------------------------------------
# Staffing data import
# ----------------------------------------------------------------------------------

try:
    from shared import df
except ImportError:
    print("Fail")

staffing_df = df.copy()

# ----------------------------------------------------------------------------------
# Options and navbar
# ----------------------------------------------------------------------------------
ui.page_opts(
    fillable=True,
)

ui.tags.style("body { margin: 0; padding: 0; } .bslib-page-fill { padding: 0; }")

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
    with ui.nav_panel("Staffing", icon=icon_svg("users")):
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

            # --- Calculate gains/losses between snapshots ---
            @reactive.calc
            def snapshot_changes():
                """Calculate headcount changes by employee type between consecutive snapshots."""
                df_f = filtered_df().copy()
                if df_f.empty:
                    return pd.DataFrame()

                df_f['date'] = pd.to_datetime(df_f['date'])
                
                counts = df_f.groupby(['date', 'employee_type']).size().unstack(fill_value=0)
                counts = counts.sort_index()
                
                if len(counts) < 2:
                    return pd.DataFrame()
                
                changes = counts.diff().fillna(0).astype(int)
                changes = changes.iloc[1:]
                
                return changes.reset_index()

            # Top 4 KPI value boxes
            with ui.layout_column_wrap(fill=False):

                with ui.value_box(showcase=icon_svg("users")):
                    "Total Headcount"
                    @render.text
                    def count():
                        current = filtered_df().shape[0]
                        changes = snapshot_changes()
                        if not changes.empty:
                            last_change = changes.iloc[-1]
                            total_change = last_change[['full_time', 'part_time', 'student']].sum()
                            symbol = "↑" if total_change > 0 else "↓" if total_change < 0 else "→"
                            color = "green" if total_change > 0 else "red" if total_change < 0 else "gray"
                            return ui.HTML(f"{current} Employees<br/><span style='color:{color}; font-size:0.9em;'>{symbol} {abs(int(total_change))} from last snapshot</span>")
                        return f"{current} Employees"

                with ui.value_box(showcase=icon_svg("clock", fill=FT_COLOR)):
                    "Full Time"
                    @render.text
                    def full_time_count():
                        current = filtered_df()[filtered_df()['employee_type'] == 'full_time'].shape[0]
                        changes = snapshot_changes()
                        if not changes.empty and 'full_time' in changes.columns:
                            ft_change = int(changes.iloc[-1]['full_time'])
                            symbol = "↑" if ft_change > 0 else "↓" if ft_change < 0 else "→"
                            color = "green" if ft_change > 0 else "red" if ft_change < 0 else "gray"
                            return ui.HTML(f"{current} Employees<br/><span style='color:{color}; font-size:0.9em;'>{symbol} {abs(ft_change)} from last snapshot</span>")
                        return f"{current} Employees"

                with ui.value_box(showcase=icon_svg("user-clock", fill=PT_COLOR)):
                    "Part Time"
                    @render.text
                    def part_time_count():
                        current = filtered_df()[filtered_df()['employee_type'] == 'part_time'].shape[0]
                        changes = snapshot_changes()
                        if not changes.empty and 'part_time' in changes.columns:
                            pt_change = int(changes.iloc[-1]['part_time'])
                            symbol = "↑" if pt_change > 0 else "↓" if pt_change < 0 else "→"
                            color = "green" if pt_change > 0 else "red" if pt_change < 0 else "gray"
                            return ui.HTML(f"{current} Employees<br/><span style='color:{color}; font-size:0.9em;'>{symbol} {abs(pt_change)} from last snapshot</span>")
                        return f"{current} Employees"

                with ui.value_box(showcase=icon_svg("graduation-cap", fill=STUDENT_COLOR)):
                    "Students"
                    @render.text
                    def student_count():
                        current = filtered_df()[filtered_df()['employee_type'] == 'student'].shape[0]
                        changes = snapshot_changes()
                        if not changes.empty and 'student' in changes.columns:
                            s_change = int(changes.iloc[-1]['student'])
                            symbol = "↑" if s_change > 0 else "↓" if s_change < 0 else "→"
                            color = "green" if s_change > 0 else "red" if s_change < 0 else "gray"
                            return ui.HTML(f"{current} Employees<br/><span style='color:{color}; font-size:0.9em;'>{symbol} {abs(s_change)} from last snapshot</span>")
                        return f"{current} Employees"

        # --- Charts row ---
            with ui.layout_columns(col_widths=(8, 4)):
                # Staffing trend over time (2/3 width)
                with ui.card():
                    ui.card_header("Staffing Trend")

                    @render_widget
                    def trend_chart():
                        df_f = filtered_df().copy()
                        if df_f.empty:
                            fig = go.Figure()
                            fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5)
                            return fig

                        df_f['date'] = pd.to_datetime(df_f['date'])

                        colors = {
                            "full_time": FT_COLOR,
                            "part_time": PT_COLOR,
                            "student":   STUDENT_COLOR,
                        }
                        labels = {
                            "full_time": "Full Time",
                            "part_time": "Part Time",
                            "student":   "Student",
                        }
                        emp_type_order = ["full_time", "part_time", "student"]

                        snapshot = (
                            df_f.groupby(['date', 'employee_type'])
                            .size()
                            .unstack(fill_value=0)
                            .reset_index()
                            .sort_values('date')
                        )

                        for et in emp_type_order:
                            if et not in snapshot.columns:
                                snapshot[et] = 0

                        fig = go.Figure()
                        for et in emp_type_order:
                            fig.add_trace(
                                go.Bar(
                                    x=snapshot['date'].dt.strftime('%Y-%m-%d'),
                                    y=snapshot[et],
                                    name=labels.get(et, et),
                                    marker_color=colors.get(et, "#333"),
                                    hovertemplate=f"<b>{labels.get(et, et)}</b><br>Count: %{{y}}<extra></extra>",
                                )
                            )

                        fig.update_layout(
                            barmode='stack',
                            xaxis_title="Date",
                            yaxis_title="Headcount",
                            xaxis_title_font=dict(size=14, color="#555555", family='Arial Black'),
                            yaxis_title_font=dict(size=14, color='#555555', family='Arial Black'),
                            hovermode='x unified',
                            height=500,
                            showlegend=True,
                            font=dict(size=10),
                        )

                        fig.update_layout(
                            height=400,
                            showlegend=True,
                            font=dict(size=10),
                        )

                        return fig

                # Student CDL Status breakdown donut chart (1/3 width)
                with ui.card():
                    ui.card_header("Student CDL Status Breakdown")

                    @render_widget
                    def donut_chart():
                        df_f = filtered_df()
                        # Filter only students
                        students_df = df_f[df_f['employee_type'] == 'student']
                        
                        if students_df.empty:
                            fig = go.Figure()
                            fig.add_annotation(text="No student data", xref="paper", yref="paper", x=0.5, y=0.5)
                            return fig

                        # Count by CDL status
                        cdl_counts = students_df['cdl_status'].value_counts()
                        
                        labels_map = {
                            "cdl": "CDL",
                            "non-cdl": "Non-CDL",
                            "training-cdl": "CDL Training",
                        }
                        colors_map = {
                            "cdl": "#0a9396",
                            "non-cdl": "#e9d8a6",
                            "training-cdl": "#94d2bd",
                        }

                        labels_list = [labels_map.get(k, k) for k in cdl_counts.index]
                        colors_list = [colors_map.get(k, "#333") for k in cdl_counts.index]

                        fig = go.Figure(
                            data=[
                                go.Pie(
                                    labels=labels_list,
                                    values=cdl_counts.values,
                                    hole=0.4,
                                    marker=dict(colors=colors_list),
                                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
                                )
                            ]
                        )

                        fig.update_layout(
                            height=400,
                            showlegend=True,
                            font=dict(size=10),
                        )

                        return fig

            # # --- Gains/Losses Trend Chart (below staffing trend) ---
            # with ui.card():
            #     ui.card_header("Staffing Changes by Employee Type")

            #     @render_widget
            #     def changes_chart():
            #         changes = snapshot_changes()
            #         if changes.empty:
            #             fig = go.Figure()
            #             fig.add_annotation(
            #                 text="Only one snapshot available. More data needed to show trends.",
            #                 xref="paper", yref="paper", x=0.5, y=0.5,
            #                 showarrow=False, font=dict(size=12, color='#999')
            #             )
            #             fig.update_layout(height=400, xaxis_visible=False, yaxis_visible=False)
            #             fig.update_layout(
            #                 height=500,
            #                 showlegend=True,
            #                 font=dict(size=10),
            #             )

            #             return fig

    # ----------------------------------------------------------------------------------
    # Page 2: Ridership
    # ----------------------------------------------------------------------------------
    with ui.nav_panel("Ridership", icon=icon_svg("chart-line")):
        ui.p("Under Construction")

    # ----------------------------------------------------------------------------------
    # Page 3: Reports
    # ----------------------------------------------------------------------------------
    with ui.nav_menu("Reports", icon=icon_svg("file-lines")):
        with ui.nav_panel("Financial Breakdown"):
            ui.p("Under Construction")
        with ui.nav_panel("On-Demand Breakdown"):
            ui.p("Under Construction")
        with ui.nav_panel("Charter Breakdown"):
            ui.p("Under Construction")

    ui.nav_spacer()

    with ui.nav_control():
        ui.a(
            icon_svg("git-alt"), " Docs",
            href="https://code.osu.edu/morgan.1461/ttm-dashboard",
            target="_blank",
            class_="nav-link"
        )
