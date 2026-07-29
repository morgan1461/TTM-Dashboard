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


# Legacy detailed UI helpers kept for future use.
# def _change_preview(names: list[str], max_names: int = 6) -> str:
#     if not names:
#         return "None"
#
#     shown = names[:max_names]
#     remaining = len(names) - len(shown)
#     text = ", ".join(shown)
#     if remaining > 0:
#         text += f", ... (+{remaining} more)"
#     return text
#
#
# def _change_details_ui(start_date: pd.Timestamp, end_date: pd.Timestamp, gained: list[str], lost: list[str]):
#     return ui.tags.div(
#         ui.tags.div(
#             f"Window: {start_date.date()} -> {end_date.date()}",
#             style="font-size: 0.75rem; color: #6c757d; margin-top: 0.3rem;",
#         ),
#         ui.tags.div(
#             f"Gained ({len(gained)}): {_change_preview(gained)}",
#             style="font-size: 0.78rem; color: #1b5e20; margin-top: 0.2rem;",
#         ),
#         ui.tags.div(
#             f"Lost ({len(lost)}): {_change_preview(lost)}",
#             style="font-size: 0.78rem; color: #b02a37; margin-top: 0.15rem;",
#         ),
#     )
#
#
# def _no_data_details_ui(message: str):
#     return ui.tags.div(
#         message,
#         style="font-size: 0.78rem; color: #6c757d; margin-top: 0.3rem;",
#     )

# ----------------------------------------------------------------------------------
# Staffing data import
# ----------------------------------------------------------------------------------

try:
    from shared import df
except ImportError:
    print("Fail")

staffing_df = df.copy()
# Normalize to date-level timestamps so date range filters include full snapshot days.
staffing_df['date'] = pd.to_datetime(staffing_df['date'], errors='coerce').dt.normalize()
# ensure all data is imported as expected

# for date in staffing_df['date'].dt.date.unique():
#     for emp_type in staffing_df['employee_type'].unique():
#         count = staffing_df[(staffing_df['date'].dt.date == date) & (staffing_df['employee_type'] == emp_type)].shape[0]
#         print(f"Date: {date}, Employee Type: {emp_type}, Count: {count}")

# ----------------------------------------------------------------------------------
# Options and navbar
# ----------------------------------------------------------------------------------
ui.page_opts(
    fillable=True,
)

ui.tags.style(
        """
body { margin: 0; padding: 0; }
.bslib-page-fill { padding: 0; }

.kpi-stack {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}

.kpi-main-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

.kpi-sub-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
}

.kpi-current {
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1;
    color: #0f172a;
}

.kpi-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 0.18rem 0.5rem;
    font-size: 0.74rem;
    font-weight: 700;
    line-height: 1.15;
}

.kpi-pill-up {
    background: #d1fae5;
    color: #065f46;
}

.kpi-pill-down {
    background: #fee2e2;
    color: #991b1b;
}

.kpi-pill-flat {
    background: #e2e8f0;
    color: #334155;
}

.kpi-pill-up-soft {
    background: #ecfdf5;
    color: #166534;
}

.kpi-pill-down-soft {
    background: #fef2f2;
    color: #b91c1c;
}
"""
)

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
                dates = staffing_df['date']
                df_f = staffing_df[
                    (dates >= start) &
                    (dates <= end) &
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

            @reactive.calc
            def name_changes_by_type():
                df_f = filtered_df().copy()
                if df_f.empty:
                    return {}

                min_date = df_f['date'].min()
                max_date = df_f['date'].max()

                start_df = df_f[df_f['date'] == min_date]
                end_df = df_f[df_f['date'] == max_date]

                changes: dict[str, dict[str, object]] = {}

                total_gained, total_lost = _name_delta(start_df, end_df)
                changes['total'] = {
                    'start_date': min_date,
                    'end_date': max_date,
                    'gained': total_gained,
                    'lost': total_lost,
                }

                for emp_type in ['full_time', 'part_time', 'student']:
                    type_start_df = start_df[start_df['employee_type'] == emp_type]
                    type_end_df = end_df[end_df['employee_type'] == emp_type]
                    gained, lost = _name_delta(type_start_df, type_end_df)
                    changes[emp_type] = {
                        'start_date': min_date,
                        'end_date': max_date,
                        'gained': gained,
                        'lost': lost,
                    }

                return changes

            # Top 4 KPI value boxes
            with ui.layout_column_wrap(fill=False):

                # Total Headcount
                with ui.value_box(showcase=icon_svg("users")):
                    "Total Headcount"
                    @render.ui
                    def count():
                        df_f = filtered_df()
                        if df_f.empty:
                            return _kpi_summary_ui(0, 0, 0, 0)

                        current = df_f[df_f['date'] == df_f['date'].max()].shape[0]
                        min_date = df_f['date'].min()
                        max_date = df_f['date'].max()
                        min_date_count = df_f[df_f['date'] == min_date].shape[0]
                        max_date_count = df_f[df_f['date'] == max_date].shape[0]
                        trend = max_date_count - min_date_count

                        changes = name_changes_by_type().get('total', None)
                        gained_count = len(changes['gained']) if changes else 0
                        lost_count = len(changes['lost']) if changes else 0

                        # Legacy detailed display kept for future re-enable.
                        # if changes:
                        #     details_ui = _change_details_ui(
                        #         changes['start_date'],
                        #         changes['end_date'],
                        #         changes['gained'],
                        #         changes['lost'],
                        #     )
                        # else:
                        #     details_ui = _no_data_details_ui("No data available for the selected timeframe")
                        #
                        # return ui.TagList(
                        #     ui.tags.div(f"{current} -> ({trend:+})"),
                        #     details_ui,
                        # )

                        return _kpi_summary_ui(current, trend, gained_count, lost_count)

                # Full time
                with ui.value_box(showcase=icon_svg("clock", fill=FT_COLOR)):
                    "Full Time Employees"
                    @render.ui
                    def full_time_count():
                        ft_df = filtered_df()[filtered_df()['employee_type'] == 'full_time']
                        if ft_df.empty:
                            return _kpi_summary_ui(0, 0, 0, 0)
                        
                        max_date = ft_df['date'].max()
                        min_date = ft_df['date'].min()
                        
                        current = ft_df[ft_df['date'] == max_date].shape[0]
                        initial = ft_df[ft_df['date'] == min_date].shape[0]
                        trend = current - initial

                        changes = name_changes_by_type().get('full_time', None)
                        gained_count = len(changes['gained']) if changes else 0
                        lost_count = len(changes['lost']) if changes else 0

                        # Legacy detailed display kept for future re-enable.
                        # if changes:
                        #     details_ui = _change_details_ui(
                        #         changes['start_date'],
                        #         changes['end_date'],
                        #         changes['gained'],
                        #         changes['lost'],
                        #     )
                        # else:
                        #     details_ui = _no_data_details_ui("No data available for the selected timeframe")
                        #
                        # return ui.TagList(
                        #     ui.tags.div(f"{current} -> ({trend:+})"),
                        #     details_ui,
                        # )

                        return _kpi_summary_ui(current, trend, gained_count, lost_count)

                # Part time
                with ui.value_box(showcase=icon_svg("user-clock", fill=PT_COLOR)):
                    "Part Time Employees"
                    @render.ui
                    def part_time_count():
                        pt_df = filtered_df()[filtered_df()['employee_type'] == 'part_time']
                        if pt_df.empty:
                            return _kpi_summary_ui(0, 0, 0, 0)

                        max_date = pt_df['date'].max()
                        min_date = pt_df['date'].min()

                        current = pt_df[pt_df['date'] == max_date].shape[0]
                        initial = pt_df[pt_df['date'] == min_date].shape[0]
                        trend = current - initial

                        changes = name_changes_by_type().get('part_time', None)
                        gained_count = len(changes['gained']) if changes else 0
                        lost_count = len(changes['lost']) if changes else 0

                        # Legacy detailed display kept for future re-enable.
                        # if changes:
                        #     details_ui = _change_details_ui(
                        #         changes['start_date'],
                        #         changes['end_date'],
                        #         changes['gained'],
                        #         changes['lost'],
                        #     )
                        # else:
                        #     details_ui = _no_data_details_ui("No data available for the selected timeframe")
                        #
                        # return ui.TagList(
                        #     ui.tags.div(f"{current} -> ({trend:+})"),
                        #     details_ui,
                        # )

                        return _kpi_summary_ui(current, trend, gained_count, lost_count)

                # Student
                with ui.value_box(showcase=icon_svg("graduation-cap", fill=STUDENT_COLOR)):
                    "Student Employees"
                    @render.ui
                    def student_count():
                        student_df = filtered_df()[filtered_df()['employee_type'] == 'student']
                        if student_df.empty:
                            return _kpi_summary_ui(0, 0, 0, 0)
                        max_date = student_df['date'].max()
                        min_date = student_df['date'].min()

                        current = student_df[student_df['date'] == max_date].shape[0]
                        initial = student_df[student_df['date'] == min_date].shape[0]
                        trend = current - initial

                        changes = name_changes_by_type().get('student', None)
                        gained_count = len(changes['gained']) if changes else 0
                        lost_count = len(changes['lost']) if changes else 0

                        # Legacy detailed display kept for future re-enable.
                        # if changes:
                        #     details_ui = _change_details_ui(
                        #         changes['start_date'],
                        #         changes['end_date'],
                        #         changes['gained'],
                        #         changes['lost'],
                        #     )
                        # else:
                        #     details_ui = _no_data_details_ui("No data available for the selected timeframe")
                        #
                        # return ui.TagList(
                        #     ui.tags.div(f"{current} -> ({trend:+})"),
                        #     details_ui,
                        # )

                        return _kpi_summary_ui(current, trend, gained_count, lost_count)

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

                        snapshot['total'] = snapshot[emp_type_order].sum(axis=1)
                        x_dates = snapshot['date'].dt.strftime('%Y-%m-%d')

                        fig = go.Figure()
                        for et in emp_type_order:
                            fig.add_trace(
                                go.Bar(
                                    x=x_dates,
                                    y=snapshot[et],
                                    name=labels.get(et, et),
                                    marker_color=colors.get(et, "#333"),
                                    marker_line=dict(color="rgba(255,255,255,0.9)", width=1),
                                    hovertemplate=f"<b>{labels.get(et, et)}</b><br>Count: %{{y}}<extra></extra>",
                                )
                            )

                        fig.add_trace(
                            go.Scatter(
                                x=x_dates,
                                y=snapshot['total'],
                                text=snapshot['total'].astype(int).astype(str),
                                mode='text',
                                textposition='top center',
                                textfont=dict(size=12, color='#1f2937', family='Arial Black'),
                                showlegend=False,
                                hoverinfo='skip',
                            )
                        )

                        fig.update_layout(
                            barmode='stack',
                            xaxis_title="Date",
                            yaxis_title="Headcount",
                            xaxis_title_font=dict(size=13, color="#334155", family='Arial'),
                            yaxis_title_font=dict(size=13, color='#334155', family='Arial'),
                            hovermode='x unified',
                            height=420,
                            showlegend=True,
                            legend=dict(
                                orientation='h',
                                yanchor='bottom',
                                y=1.03,
                                xanchor='left',
                                x=0,
                            ),
                            margin=dict(l=40, r=20, t=36, b=40),
                            plot_bgcolor='rgba(248,250,252,1)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(size=11, color='#334155'),
                        )

                        fig.update_xaxes(showgrid=False, tickangle=-30)
                        fig.update_yaxes(
                            gridcolor='rgba(148,163,184,0.25)',
                            zeroline=False,
                            rangemode='tozero',
                            range=[0, max(snapshot['total'].max() * 1.14, 1)],
                        )

                        return fig

                # Student CDL Status breakdown donut chart (1/3 width)
                with ui.card():
                    ui.card_header("Student CDL Status Breakdown")

                    @render_widget
                    def donut_chart():
                        df_f = filtered_df()
                        # Filter only students
                        students_df = df_f[(df_f['employee_type'] == 'student') & (df_f['date'] == df_f['date'].max())]
                        
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
                            "cdl": FT_COLOR,
                            "non-cdl": PT_COLOR,
                            "training-cdl": STUDENT_COLOR,
                        }

                        status_order = ["cdl", "non-cdl", "training-cdl"]
                        ordered_statuses = [s for s in status_order if s in cdl_counts.index] + [
                            s for s in cdl_counts.index if s not in status_order
                        ]
                        ordered_counts = cdl_counts.reindex(ordered_statuses)

                        labels_list = [labels_map.get(k, k) for k in ordered_counts.index]
                        colors_list = [colors_map.get(k, "#64748b") for k in ordered_counts.index]
                        total_students = int(ordered_counts.sum())

                        fig = go.Figure(
                            data=[
                                go.Pie(
                                    labels=labels_list,
                                    values=ordered_counts.values,
                                    hole=0.58,
                                    marker=dict(colors=colors_list, line=dict(color='white', width=2)),
                                    sort=False,
                                    direction='clockwise',
                                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
                                    textinfo='percent',
                                    textfont=dict(size=11, color='white'),
                                )
                            ]
                        )

                        fig.add_annotation(
                            text=f"<b>{total_students}</b><br><span style='font-size:11px;color:#475569;'>students</span>",
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                        )

                        fig.update_layout(
                            height=420,
                            showlegend=True,
                            legend=dict(
                                orientation='h',
                                yanchor='bottom',
                                y=1.03,
                                xanchor='left',
                                x=0,
                            ),
                            margin=dict(l=20, r=20, t=36, b=20),
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(size=11, color='#334155'),
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
            ui.p("Concept")
        with ui.nav_panel("On-Demand Breakdown"):
            ui.p("Concept")
        with ui.nav_panel("Charter Breakdown"):
            ui.p("Concept")

    ui.nav_spacer()

    with ui.nav_control():
        ui.a(
            icon_svg("git-alt"), " Docs",
            href="https://code.osu.edu/morgan.1461/ttm-dashboard",
            target="_blank",
            class_="nav-link"
        )
