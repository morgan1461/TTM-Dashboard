import pandas as pd
import plotly.graph_objects as go  # type: ignore

from shiny import reactive
from shiny.express import module, render, ui
from faicons import icon_svg
from shinywidgets import render_widget  # type: ignore

from colors import (
    TOTAL_COLOR,
    FT_COLOR,
    PT_COLOR,
    STUDENT_COLOR,
    STUDENT_CDL_COLOR,
    STUDENT_TRAINING_CDL_COLOR,
    STUDENT_NON_CDL_COLOR,
)
from ui_helpers import _name_delta, _kpi_summary_ui


@module
def staffing_tab(input, output, session, staffing_df: pd.DataFrame):
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

                ui.input_radio_buttons(
                    "retention_metric",
                    "Retention View",
                    choices={"count": "Counts", "percent": "Percentages"},
                    selected="percent",
                    inline=True,
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

                        return _kpi_summary_ui(current, trend, gained_count, lost_count)

        # --- Charts row ---
            with ui.layout_columns(col_widths=(8, 4), fill=False):
                # Staffing trend over time (2/3 width)
                with ui.card(full_screen=True, class_="dashboard-card"):
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
                with ui.card(full_screen=True, class_="dashboard-card"):
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

                # Staff retention metrics over time
                with ui.card(full_screen=True, class_="dashboard-card"):
                    ui.card_header("Staff Retention")
                    @render_widget
                    def retention():
                        df_f = filtered_df().copy()

                        if df_f.empty or 'hire_date' not in df_f.columns:
                            fig = go.Figure()
                            fig.add_annotation(
                                text="No retention data available",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False,
                            )
                            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                            return fig

                        staff_df = df_f[df_f['employee_type'].isin(['full_time', 'part_time'])].copy()
                        if staff_df.empty:
                            fig = go.Figure()
                            fig.add_annotation(
                                text="No staff in the selected range",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False,
                            )
                            return fig

                        staff_df['date'] = pd.to_datetime(staff_df['date'])
                        staff_df['hire_date'] = pd.to_datetime(staff_df['hire_date'], errors='coerce')
                        staff_df = staff_df[staff_df['hire_date'].notna()].copy()

                        if staff_df.empty:
                            fig = go.Figure()
                            fig.add_annotation(
                                text="No staff tenure data available",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False,
                            )
                            return fig

                        def categorize_tenure(days):
                            if pd.isna(days):
                                return None
                            if days < 365:
                                return '<1 Year'
                            if days < 1825:
                                return '1-5 Years'
                            return '5+ Years'

                        staff_df['tenure_days'] = (staff_df['date'] - staff_df['hire_date']).dt.days
                        staff_df['Tenure_Bucket'] = staff_df['tenure_days'].apply(categorize_tenure)
                        staff_df = staff_df[staff_df['Tenure_Bucket'].notna()].copy()

                        if staff_df.empty:
                            fig = go.Figure()
                            fig.add_annotation(
                                text="No staff in a retention bucket",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False,
                            )
                            return fig

                        buckets = ['<1 Year', '1-5 Years', '5+ Years']
                        colors = {
                            '<1 Year': '#9ecae1',
                            '1-5 Years': '#3182bd',
                            '5+ Years': '#08519c',
                        }
                        metric = input.retention_metric()
                        dates = sorted(staff_df['date'].drop_duplicates().tolist())

                        fig = go.Figure()
                        for bucket in buckets:
                            values = []
                            for snapshot_date in dates:
                                slice_df = staff_df[staff_df['date'] == snapshot_date]
                                total_for_date = len(slice_df)
                                count = int((slice_df['Tenure_Bucket'] == bucket).sum())
                                if metric == 'percent':
                                    value = (count / total_for_date * 100) if total_for_date else 0
                                else:
                                    value = count
                                values.append(value)

                            fig.add_trace(
                                go.Scatter(
                                    x=pd.to_datetime(dates),
                                    y=values,
                                    mode='lines+markers',
                                    name=bucket,
                                    line=dict(width=3, color=colors[bucket]),
                                    marker=dict(size=7, color=colors[bucket]),
                                    hovertemplate=(
                                        f"<b>{bucket}</b><br>%{{x|%Y-%m-%d}}<br>"
                                        + ("Count: %{y:.0f}<extra></extra>" if metric == 'count' else "Percent: %{y:.1f}%<extra></extra>")
                                    ),
                                )
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
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(size=11, color='#334155'),
                            xaxis=dict(title='Date', tickangle=-30),
                            yaxis=dict(
                                title='Percentage of Staff (%)' if metric == 'percent' else 'Headcount',
                                showgrid=True,
                                gridcolor='#e2e8f0',
                                range=[0, max(100, max([v for trace in fig.data for v in trace.y]) * 1.2 if fig.data else 1)] if metric == 'percent' else [0, max([v for trace in fig.data for v in trace.y]) * 1.2 if fig.data else 1],
                            )
                        )

                        return fig

                # Records table - for all employees
                with ui.card(full_screen=True, class_="dashboard-card"):
                    ui.card_header("Employee Records Table")

                    @render.data_frame
                    def summary_statistics():

                        df_f = filtered_df()
                        if df_f.empty:
                            empty_df = pd.DataFrame(columns=['Name', 'Employee type', 'CDL status', 'Hire date'])
                            return render.DataGrid(empty_df, filters=True)

                        latest_date = df_f['date'].max()
                        display_df = df_f[df_f['date'] == latest_date][['full_name', 'employee_type', 'cdl_status', 'hire_date']].copy()
                        display_df = display_df.dropna(subset=['full_name']).sort_values('full_name').reset_index(drop=True)
                        employee_type_labels = {
                            'full_time': 'Full time',
                            'part_time': 'Part time',
                            'student': 'Student',
                        }
                        cdl_status_labels = {
                            'cdl': 'CDL',
                            'non-cdl': 'Non-CDL',
                            'training-cdl': 'CDL training',
                        }
                        display_df['employee_type'] = display_df['employee_type'].replace(employee_type_labels)
                        display_df['cdl_status'] = display_df['cdl_status'].replace(cdl_status_labels)
                        display_df['hire_date'] = pd.to_datetime(display_df['hire_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                        display_df = display_df.rename(columns={
                            'full_name': 'Name',
                            'employee_type': 'Employee type',
                            'cdl_status': 'CDL status',
                            'hire_date': 'Hire date',
                        })
                        return render.DataGrid(display_df, filters=True)
