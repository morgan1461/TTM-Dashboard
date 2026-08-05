import pandas as pd 
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date
from pathlib import Path
import plotly.graph_objects as go # type: ignore

from shiny.express import ui, render, input
from shiny import reactive
from faicons import icon_svg
from shinywidgets import render_widget # type: ignore

pd.set_option("display.max_columns", None)

NAVBAR_COLOR = "#0F172A"
BG_COLOR = "#F8FAFC"

TOTAL_COLOR = "#475569"
FT_COLOR = "#1E3A8A"
PT_COLOR = "#0284C7"
STUDENT_COLOR = "#0F766E"

STUDENT_CDL_COLOR = "#047857"
STUDENT_TRAINING_CDL_COLOR = "#C2410C"
STUDENT_NON_CDL_COLOR = "#B45309"


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
#  data import
# ----------------------------------------------------------------------------------
# staffing data
try:
    from shared import staffing_df
except ImportError:
    print("Fail: Staffing data not found")

staffing_df = staffing_df.copy()
# ensure all data is imported as expected

# for date in staffing_df['date'].dt.date.unique():
#     for emp_type in staffing_df['employee_type'].unique():
#         count = staffing_df[(staffing_df['date'].dt.date == date) & (staffing_df['employee_type'] == emp_type)].shape[0]
#         print(f"Date: {date}, Employee Type: {emp_type}, Count: {count}")

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
                with ui.value_box(showcase=icon_svg("users").add_style(f"fill: {TOTAL_COLOR} !important;")):
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
                with ui.value_box(showcase=icon_svg("clock").add_style(f"fill: {FT_COLOR} !important;")):
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
                with ui.value_box(showcase=icon_svg("user-clock").add_style(f"fill: {PT_COLOR} !important;")):
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
                with ui.value_box(showcase=icon_svg("graduation-cap").add_style(f"fill: {STUDENT_COLOR} !important;")):
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
                with ui.card(full_screen=True):
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
                            autosize=True,
                            barmode='stack',
                            xaxis_title="Date",
                            yaxis_title="Headcount",
                            xaxis_title_font=dict(size=13, color="#334155", family='Arial'),
                            yaxis_title_font=dict(size=13, color='#334155', family='Arial'),
                            hovermode='x unified',
                            height=470,
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
                with ui.card(full_screen=True):
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
                            "cdl": STUDENT_CDL_COLOR,
                            "non-cdl": STUDENT_NON_CDL_COLOR,
                            "training-cdl": STUDENT_TRAINING_CDL_COLOR,
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
                            autosize=True,
                            height=470,
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

                # Full time staffing retention metrics
                with ui.card(full_screen=True):
                    ui.card_header("Staff Retention")
                    @render_widget
                    def retention():
                        df_f = filtered_df().copy()
                        
                        # 1. Failsafe checks
                        if df_f.empty or 'hire_date' not in df_f.columns:
                            fig = go.Figure()
                            fig.add_annotation(
                                text="No retention data available", 
                                xref="paper", yref="paper", 
                                x=0.5, y=0.5, showarrow=False
                            )
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                            return fig

                        # 2. Filter for only Full Time employees in the most recent snapshot
                        max_date = df_f['date'].max()
                        ft_df = df_f[df_f['date'] == max_date].copy()
                        
                        if ft_df.empty:
                            fig = go.Figure()
                            fig.add_annotation(text="No full-time staff in current snapshot", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                            return fig

                        # 3. Calculate Tenure dynamically
                        # Ensure dates are datetime objects
                        ft_df['hire_date'] = pd.to_datetime(ft_df['hire_date'], errors='coerce')
                        ft_df['date'] = pd.to_datetime(ft_df['date'])
                        
                        # Calculate days between hire date and snapshot date
                        ft_df['tenure_days'] = (ft_df['date'] - ft_df['hire_date']).dt.days
                        
                        # 4. Create Tenure Buckets
                        def categorize_tenure(days):
                            if pd.isna(days):
                                return 'Unknown'
                            elif days < 365:
                                return '<1 Year'
                            elif days < 1825: # 5 years * 365
                                return '1-5 Years'
                            else:
                                return '5+ Years'
                                
                        ft_df['Tenure_Bucket'] = ft_df['tenure_days'].apply(categorize_tenure)
                        
                        # 5. Aggregate the counts and calculate percentages
                        bucket_counts = ft_df['Tenure_Bucket'].value_counts()
                        total_staff = len(ft_df)
                        
                        # Calculate percentages safely
                        pct_under_1 = (bucket_counts.get('<1 Year', 0) / total_staff) * 100 if total_staff > 0 else 0
                        pct_1_to_5 = (bucket_counts.get('1-5 Years', 0) / total_staff) * 100 if total_staff > 0 else 0
                        pct_5_plus = (bucket_counts.get('5+ Years', 0) / total_staff) * 100 if total_staff > 0 else 0

                        # Define sequential colors
                        colors = {
                            '<1 Year': '#9ecae1',   # Light blue
                            '1-5 Years': '#3182bd', # Medium blue
                            '5+ Years': '#08519c'   # Dark blue
                        }

                        # 6. Build the Plotly figure
                        fig = go.Figure()

                        # Add traces for each bucket (Using "Overall" as the X-axis label)
                        fig.add_trace(go.Bar(
                            x=["Overall"], 
                            y=[pct_under_1], 
                            name='<1 Year', 
                            marker_color=colors['<1 Year'],
                            hovertemplate="<b>%{x}</b><br><1 Year: %{y:.1f}%<extra></extra>"
                        ))
                        
                        fig.add_trace(go.Bar(
                            x=["Overall"], 
                            y=[pct_1_to_5], 
                            name='1-5 Years', 
                            marker_color=colors['1-5 Years'],
                            hovertemplate="<b>%{x}</b><br>1-5 Years: %{y:.1f}%<extra></extra>"
                        ))
                        
                        fig.add_trace(go.Bar(
                            x=["Overall"], 
                            y=[pct_5_plus], 
                            name='5+ Years', 
                            marker_color=colors['5+ Years'],
                            hovertemplate="<b>%{x}</b><br>5+ Years: %{y:.1f}%<extra></extra>"
                        ))

                        # Apply layout styling
                        fig.update_layout(
                            autosize=True,
                            barmode='stack',
                            height=470,
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
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(size=11, color='#334155'),
                            yaxis=dict(
                                title="Percentage of Staff (%)",
                                range=[0, 100],
                                showgrid=True,
                                gridcolor='#e2e8f0'
                            )
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
    # Page 2: Student Trends
    # ----------------------------------------------------------------------------------

    with ui.nav_panel("Student Trends", icon=icon_svg("chart-simple")):

        ui.p("Note: this counts student supervisors as to why the numbers do not add up from previous staffing page")
        
        # --- Reactive dataframe (No Date Filtering) ---
        # --- Reactive dataframe (No Date Filtering) ---
        @reactive.calc
        def student_snapshot_df():
            # Use a new local variable name 'df' to avoid UnboundLocalError
            df = student_trends_df.copy()
            df = df[df['active'] == 1]

            return df

        # --- Top KPIs ---
        with ui.layout_column_wrap(fill=False):
            with ui.value_box(showcase=icon_svg("user-graduate").add_style(f"fill: {STUDENT_COLOR} !important;")):
                "Total Active Students"
                @render.ui
                def active_students_kpi():
                    df_f = student_snapshot_df()
                    if df_f.empty or 'active' not in df_f.columns:
                        return ui.tags.div(ui.tags.span("0", class_="kpi-current"))
                    
                    active_count = df_f[df_f['active'] == 1].shape[0]
                    return ui.tags.div(ui.tags.span(str(active_count), class_="kpi-current"))
                    
            with ui.value_box(showcase=icon_svg("id-card").add_style(f"fill: {STUDENT_NON_CDL_COLOR} !important;")):
                "Active Students w/ Permit"
                @render.ui
                def permit_students_kpi():
                    df_f = student_snapshot_df()
                    if df_f.empty or 'permit' not in df_f.columns:
                        return ui.tags.div(ui.tags.span("0", class_="kpi-current"))
                    
                    permit_count = df_f[(df_f['active'] == 1) & (df_f['permit'] == True)].shape[0]
                    return ui.tags.div(ui.tags.span(str(permit_count), class_="kpi-current"))
                    
            with ui.value_box(showcase=icon_svg("truck").add_style(f"fill: {STUDENT_CDL_COLOR} !important;")):
                "Active Students w/ CDL"
                @render.ui
                def cdl_students_kpi():
                    df_f = student_snapshot_df()
                    if df_f.empty or 'cdl' not in df_f.columns:
                        return ui.tags.div(ui.tags.span("0", class_="kpi-current"))
                    
                    cdl_count = df_f[(df_f['active'] == 1) & (df_f['cdl'] == True)].shape[0]
                    return ui.tags.div(ui.tags.span(str(cdl_count), class_="kpi-current"))
                    
            with ui.value_box(showcase=icon_svg("stopwatch").add_style(f"fill: {TOTAL_COLOR} !important;")):
                "Avg. Total Training Days"
                @render.ui
                def avg_training_days_kpi():
                    df_f = student_snapshot_df()
                    if df_f.empty or 'total_training_days' not in df_f.columns:
                        return ui.tags.div(ui.tags.span("N/A", class_="kpi-current"))
                    
                    avg_days = df_f['total_training_days'].mean()
                    val = f"{avg_days:.1f}" if pd.notna(avg_days) else "N/A"
                    return ui.tags.div(
                        ui.tags.span(val, class_="kpi-current"),
                        ui.tags.span(" days", style="font-size: 1rem; color: #64748b; margin-left: 0.3rem;")
                    )

        # --- Charts Row ---
        with ui.layout_columns(col_widths=(7, 5), gap="2rem"):
            # Training Pipeline Funnel
            with ui.card(full_screen=True):
                ui.card_header("Student Training Pipeline")
                @render_widget
                def training_funnel_chart():
                    df_f = student_snapshot_df()
                    if df_f.empty:
                        fig = go.Figure()
                        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                        return fig
                        
                    # Extract pipeline based on successful milestones recorded in the dataset
                    orientation = df_f['orientation_date'].notna().sum() if 'orientation_date' in df_f.columns else 0
                    permit = df_f['student_cdl_permit_date'].notna().sum() if 'student_cdl_permit_date' in df_f.columns else 0
                    training = df_f['cdl_training_start_date'].notna().sum() if 'cdl_training_start_date' in df_f.columns else 0
                    cdl = df_f['student_cdl_date'].notna().sum() if 'student_cdl_date' in df_f.columns else 0
                    
                    stages = ["Orientation", "Permit Acquired", "CDL Training", "CDL Acquired"]
                    values = [orientation, permit, training, cdl]
                    
                    fig = go.Figure(go.Funnel(
                        y=stages,
                        x=values,
                        textinfo="value+percent initial",
                        marker=dict(color=[STUDENT_COLOR, STUDENT_NON_CDL_COLOR, STUDENT_TRAINING_CDL_COLOR, STUDENT_CDL_COLOR])
                    ))
                    
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=36, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12, color='#334155'),
                        height=400
                    )
                    return fig

            # Average Days Chart
            with ui.card(full_screen=True):
                ui.card_header("Average Days Between Milestones")
                @render_widget
                def days_milestones_chart():
                    df_f = student_snapshot_df()
                    if df_f.empty:
                        fig = go.Figure()
                        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                        return fig
                        
                    # Compute historical progression averages
                    permit_to_cdl = df_f['days_permit_to_cdl'].mean() if 'days_permit_to_cdl' in df_f.columns else 0
                    total_training = df_f['total_training_days'].mean() if 'total_training_days' in df_f.columns else 0
                    
                    metrics = {
                        "Permit to CDL": permit_to_cdl,
                        "Total Training": total_training
                    }
                    
                    y_labels = list(metrics.keys())
                    x_values = [val if pd.notna(val) else 0 for val in metrics.values()]
                    text_values = [f"{val:.1f} days" if pd.notna(val) else "N/A" for val in metrics.values()]
                    
                    fig = go.Figure(go.Bar(
                        x=x_values,
                        y=y_labels,
                        orientation='h',
                        text=text_values,
                        textposition='auto',
                        marker_color=[STUDENT_TRAINING_CDL_COLOR, STUDENT_CDL_COLOR]
                    ))
                    
                    fig.update_layout(
                        xaxis_title="Average Days",
                        margin=dict(l=20, r=20, t=36, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(248,250,252,1)',
                        font=dict(size=12, color='#334155'),
                        height=400,
                        xaxis=dict(gridcolor='rgba(148,163,184,0.25)', zeroline=False)
                    )
                    return fig
    # ----------------------------------------------------------------------------------
    # Page 3: Ridership
    # ----------------------------------------------------------------------------------
    with ui.nav_panel("Ridership", icon=icon_svg("chart-line")):
        ui.p("Under Construction")

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
