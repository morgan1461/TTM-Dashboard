import pandas as pd
import plotly.graph_objects as go  # type: ignore

from shiny import reactive
from shiny.express import module, render, ui
from faicons import icon_svg
from shinywidgets import render_widget  # type: ignore

from colors import (
    STUDENT_COLOR,
    STUDENT_CDL_COLOR,
    STUDENT_TRAINING_CDL_COLOR,
    STUDENT_NON_CDL_COLOR,
)


@module
def student_trends_tab(input, output, session, student_trends_df: pd.DataFrame):
    with ui.nav_panel("Student Trends", icon=icon_svg("chart-simple")):
        with ui.layout_sidebar():
            with ui.sidebar(width=270, open='desktop'):
                ui.h5("Student Filters", style="margin-top: 0;")
                ui.input_radio_buttons(
                    "student_scope",
                    "Student View",
                    choices={"active": "Active", "all": "Historical"},
                    selected="active",
                    inline=True,
                )
                ui.hr()

            @reactive.calc
            def active_only_selected() -> bool:
                return input.student_scope() == 'active'

            @reactive.calc
            def student_snapshot_df():
                df = student_trends_df.copy()

                if active_only_selected() and 'active' in df.columns:
                    active_numeric = pd.to_numeric(df['active'], errors='coerce')
                    if active_numeric.notna().any():
                        active_mask = active_numeric.fillna(0).eq(1)
                    else:
                        active_text = df['active'].astype(str).str.strip().str.lower()
                        active_mask = active_text.isin({'1', 'true', 'yes', 'y', 'active'})
                    df = df[active_mask].copy()

                for col in [
                    'orientation_date',
                    'student_permit_deadline',
                    'student_cdl_permit_date',
                    'dot_cert',
                    'cdl_training_start_date',
                    'student_cdl_date',
                ]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')

                return df

            @reactive.calc
            def student_workflow_metrics():
                df = student_snapshot_df()
                cdl = df.get('cdl', pd.Series(False, index=df.index)).fillna(False).astype(bool)
                non_cdl_track = df.get(
                    'non_cdl_track',
                    pd.Series(False, index=df.index),
                ).fillna(False).astype(bool)
                totals = {
                    'CDL': int(cdl.sum()),
                    'Non-CDL': int((~cdl).sum()),
                    'non-cdl track': int(non_cdl_track.sum()),
                }
                maximum = max(totals.values(), default=0)
                return [
                    {'label': label, 'total': total, 'width': (total / maximum * 100 if maximum else 0), 'color': color}
                    for (label, total), color in zip(totals.items(), [STUDENT_CDL_COLOR, STUDENT_NON_CDL_COLOR, STUDENT_TRAINING_CDL_COLOR])
                ]

            @reactive.calc
            def student_stage_counts():
                df = student_snapshot_df()
                stage_order = ['orientation', 'cdl_permit', 'dot_cert', 'cdl_training']
                status = df.get('status', pd.Series(index=df.index, dtype=object)).fillna('').astype(str).str.strip().str.lower()

                if status.eq('').all():
                    status = pd.Series('orientation', index=df.index)
                    status = status.mask(df.get('student_cdl_permit_date', pd.Series(index=df.index)).notna(), 'cdl_permit')
                    status = status.mask(df.get('dot_cert', pd.Series(index=df.index)).notna(), 'dot_cert')
                    status = status.mask(df.get('cdl_training_start_date', pd.Series(index=df.index)).notna(), 'cdl_training')
                    status = status.mask(df.get('cdl', pd.Series(False, index=df.index)).fillna(False).astype(bool), 'cdl')

                return {
                    stage: int((status == stage).sum())
                    for stage in stage_order
                }

            @reactive.calc
            def student_duration_summary():
                df = student_snapshot_df()
                durations = (
                    df['student_cdl_date'] - df['orientation_date']
                ).dt.days.dropna()
                durations = durations[durations >= 0]

                if durations.empty:
                    return {'average': None, 'median': None, 'minimum': None, 'maximum': None, 'completed': 0}

                return {
                    'average': durations.mean(),
                    'median': durations.median(),
                    'minimum': int(durations.min()),
                    'maximum': int(durations.max()),
                    'completed': int(durations.size),
                }

            @reactive.calc
            def student_pipeline_metrics():
                df = student_snapshot_df()
                stages = [
                    ('Orientation', 'orientation_date'),
                    ('CDL Permit', 'student_cdl_permit_date'),
                    ('DOT Cert', 'dot_cert'),
                    ('Training', 'cdl_training_start_date'),
                    ('CDL', 'student_cdl_date'),
                ]

                def stage_series(column_name: str) -> pd.Series:
                    return pd.to_datetime(
                        df.get(column_name, pd.Series(index=df.index, dtype='datetime64[ns]')),
                        errors='coerce',
                    )

                transitions = []
                for (from_label, from_column), (to_label, to_column) in zip(stages, stages[1:]):
                    from_series = stage_series(from_column)
                    to_series = stage_series(to_column)
                    durations = (to_series - from_series).dt.days.dropna()
                    durations = durations[durations >= 0]
                    transitions.append({
                        'from': from_label,
                        'to': to_label,
                        'average': durations.mean() if not durations.empty else None,
                        'minimum': int(durations.min()) if not durations.empty else None,
                        'maximum': int(durations.max()) if not durations.empty else None,
                        'completed': int(durations.size),
                    })

                stage_counts = []
                for label, column in stages:
                    column_series = stage_series(column)
                    stage_counts.append({
                        'label': label,
                        'completed': int(column_series.notna().sum()),
                    })

                return {'transitions': transitions, 'stage_counts': stage_counts}

            @reactive.calc
            def student_timeline_metrics():
                df = student_snapshot_df()
                if df.empty:
                    return {
                        'labels': [],
                        'days': [],
                        'intervals': {},
                        'deadline_days': None,
                        'total_days': 0,
                    }

                for col in [
                    'orientation_date',
                    'student_permit_deadline',
                    'student_cdl_permit_date',
                    'dot_cert',
                    'cdl_training_start_date',
                    'student_cdl_date',
                ]:
                    if col not in df.columns:
                        df[col] = pd.NaT

                valid = df.dropna(
                    subset=['orientation_date', 'student_cdl_permit_date', 'cdl_training_start_date', 'student_cdl_date']
                ).copy()
                if valid.empty:
                    return {
                        'labels': [],
                        'days': [],
                        'intervals': {},
                        'deadline_days': None,
                        'total_days': 0,
                    }

                valid['orientation_to_permit'] = (valid['student_cdl_permit_date'] - valid['orientation_date']).dt.days
                valid['permit_to_dot'] = (valid['dot_cert'] - valid['student_cdl_permit_date']).dt.days
                valid['dot_to_training'] = (valid['cdl_training_start_date'] - valid['dot_cert']).dt.days
                valid['training_to_cdl'] = (valid['student_cdl_date'] - valid['cdl_training_start_date']).dt.days

                for interval_col in ['orientation_to_permit', 'permit_to_dot', 'dot_to_training', 'training_to_cdl']:
                    valid[interval_col] = valid[interval_col].where(valid[interval_col] >= 0)

                intervals = {
                    'orientation_to_permit': valid['orientation_to_permit'].mean(),
                    'permit_to_dot': valid['permit_to_dot'].mean(),
                    'dot_to_training': valid['dot_to_training'].mean(),
                    'training_to_cdl': valid['training_to_cdl'].mean(),
                }

                total = sum(v for v in intervals.values() if pd.notna(v))

                deadline_series = df.dropna(subset=['orientation_date', 'student_permit_deadline'])
                deadline_days = None
                if not deadline_series.empty:
                    deadline_days = (deadline_series['student_permit_deadline'] - deadline_series['orientation_date']).dt.days.mean()

                labels = [
                    'Orientation',
                    'CDL Permit',
                    'DOT Cert',
                    'CDL Training',
                    'CDL',
                ]
                days = [
                    0,
                    intervals['orientation_to_permit'],
                    intervals['orientation_to_permit'] + intervals['permit_to_dot'],
                    intervals['orientation_to_permit'] + intervals['permit_to_dot'] + intervals['dot_to_training'],
                    total,
                ]

                return {
                    'labels': labels,
                    'days': days,
                    'intervals': intervals,
                    'deadline_days': deadline_days,
                    'total_days': total,
                }

            @reactive.calc
            def student_transition_table_df():
                metrics = student_pipeline_metrics()
                rows = []

                for transition in metrics['transitions']:
                    average = transition['average']
                    if average is None or pd.isna(average):
                        average_days = None
                        speed_band = 'No data'
                    else:
                        average_days = int(round(average))
                        if average_days <= 7:
                            speed_band = 'Fast'
                        elif average_days <= 14:
                            speed_band = 'On Track'
                        else:
                            speed_band = 'Watch'

                    rows.append({
                        'transition': f"{transition['from']} -> {transition['to']}",
                        'average_days': average_days,
                        'range': (
                            f"{transition['minimum']}-{transition['maximum']}"
                            if transition['minimum'] is not None and transition['maximum'] is not None
                            else 'N/A'
                        ),
                        'completed': transition['completed'],
                        'speed_band': speed_band,
                    })

                return pd.DataFrame(rows)

            with ui.tags.div(class_="student-trends-scroll"):
                with ui.layout_column_wrap(fill=False):
                    # with ui.value_box(showcase=icon_svg("user-graduate").add_style(f"fill: {STUDENT_COLOR} !important;")):
                    #     "Active Students"
                    #     @render.ui
                    #     def active_students_kpi():
                    #         df_f = student_snapshot_df()
                    #         if df_f.empty:
                    #             return ui.tags.div(ui.tags.span("0", class_="kpi-current"))
                    #         return ui.tags.div(ui.tags.span(str(int(df_f.shape[0])), class_="kpi-current"))

                    # with ui.value_box(showcase=icon_svg("id-card").add_style(f"fill: {STUDENT_NON_CDL_COLOR} !important;")):
                    #     "Avg. Orientation -> Permit"
                    #     @render.ui
                    #     def permit_timing_kpi():
                    #         metrics = student_timeline_metrics()
                    #         interval = metrics['intervals'].get('orientation_to_permit')
                    #         if interval is None or pd.isna(interval):
                    #             return ui.tags.div(ui.tags.span("N/A", class_="kpi-current"))
                    #         val = int(round(interval))
                    #         return ui.tags.div(
                    #             ui.tags.span(f"{val} days", class_="kpi-current"),
                    #             ui.tags.span(" average", style="font-size: 0.8rem; color: #64748b; margin-left: 0.25rem;"),
                    #         )

                    # with ui.value_box(showcase=icon_svg("truck").add_style(f"fill: {STUDENT_CDL_COLOR} !important;")):
                    #     "Avg. Training -> CDL"
                    #     @render.ui
                    #     def training_to_cdl_kpi():
                    #         metrics = student_timeline_metrics()
                    #         interval = metrics['intervals'].get('training_to_cdl')
                    #         if interval is None or pd.isna(interval):
                    #             return ui.tags.div(ui.tags.span("N/A", class_="kpi-current"))
                    #         val = int(round(interval))
                    #         return ui.tags.div(
                    #             ui.tags.span(f"{val} days", class_="kpi-current"),
                    #             ui.tags.span(" average", style="font-size: 0.8rem; color: #64748b; margin-left: 0.25rem;"),
                    #         )

                    with ui.card():
                        ui.card_header("Student Employee Overview")

                        @render.ui
                        def student_workflow_overview():
                            rows = []
                            for metric in student_workflow_metrics():
                                rows.append(
                                    ui.tags.div(
                                        ui.tags.div(metric['label'], class_="student-workflow-label"),
                                        ui.tags.div(
                                            ui.tags.div(
                                                style=f"width: {metric['width']:.1f}%; background-color: {metric['color']};",
                                                class_="student-workflow-bar",
                                            ),
                                            class_="student-workflow-track",
                                        ),
                                        ui.tags.span(str(metric['total']), class_="student-workflow-total"),
                                        class_="student-workflow-row",
                                    )
                                )
                            return ui.tags.div(*rows, class_="student-workflow-list")

                    with ui.card():
                        ui.card_header("Current Student Stage")

                        @render.ui
                        def student_stage_counts_chart():
                            stages = [
                                ('Orientation', 'orientation', STUDENT_COLOR),
                                ('Permit', 'cdl_permit', STUDENT_NON_CDL_COLOR),
                                ('DOT', 'dot_cert', '#2563EB'),
                                ('Training', 'cdl_training', STUDENT_TRAINING_CDL_COLOR),
                            ]
                            counts = student_stage_counts()
                            maximum = max(counts.values(), default=0)
                            rows = [
                                ui.tags.div(
                                    ui.tags.div(label, class_="student-workflow-label"),
                                    ui.tags.div(
                                        ui.tags.div(
                                            style=f"width: {(counts[key] / maximum * 100 if maximum else 0):.1f}%; background-color: {color};",
                                            class_="student-workflow-bar",
                                        ),
                                        class_="student-workflow-track",
                                    ),
                                    ui.tags.span(str(counts[key]), class_="student-workflow-total"),
                                    class_="student-workflow-row",
                                )
                                for label, key, color in stages
                            ]
                            return ui.tags.div(*rows, class_="student-workflow-list")

                    with ui.card():
                        ui.card_header("CDL Timeline")

                        @render.ui
                        def student_duration_summary_ui():
                            summary = student_duration_summary()
                            if summary['completed'] == 0:
                                return ui.tags.div("No completed orientation-to-CDL timelines", class_="student-duration-empty")

                            def days(value):
                                return f"{int(round(value))} days"

                            return ui.tags.div(
                                ui.tags.div(
                                    ui.tags.span("Average", class_="student-duration-label"),
                                    ui.tags.span(days(summary['average']), class_="student-duration-value"),
                                    class_="student-duration-stat student-duration-stat-primary",
                                ),
                                ui.tags.div(
                                    ui.tags.span("Median", class_="student-duration-label"),
                                    ui.tags.span(days(summary['median']), class_="student-duration-value"),
                                    class_="student-duration-stat",
                                ),
                                ui.tags.div(
                                    ui.tags.span("Range", class_="student-duration-label"),
                                    ui.tags.span(
                                        f"{days(summary['minimum'])} - {days(summary['maximum'])}",
                                        class_="student-duration-value",
                                    ),
                                    class_="student-duration-stat",
                                ),
                                class_="student-duration-summary",
                            )

                with ui.card(full_screen=True):
                    ui.card_header("Student Progression Timeline")

                    @render.ui
                    def student_pipeline_velocity():
                        metrics = student_pipeline_metrics()
                        transitions = metrics['transitions']
                        stage_counts = metrics['stage_counts']

                        def transition_label(transition):
                            if transition['completed'] == 0:
                                return "No completed transitions"
                            return (
                                f"Avg {int(round(transition['average']))} days · "
                                f"Range {transition['minimum']}-{transition['maximum']} days · "
                                f"n={transition['completed']}"
                            )

                        flow = []
                        for index, stage in enumerate(stage_counts):
                            flow.append(
                                ui.tags.div(
                                    ui.tags.div(
                                        ui.tags.div(stage['label'], class_="student-pipeline-stage-name"),
                                        ui.tags.div(
                                            f"{stage['completed']} employees",
                                            class_="student-pipeline-stage-count",
                                        ),
                                        class_="student-pipeline-stage-node",
                                    ),
                                    class_="student-pipeline-stage",
                                )
                            )
                            if index < len(transitions):
                                transition = transitions[index]
                                flow.append(
                                    ui.tags.div(
                                        ui.tags.div(class_="student-pipeline-arrow"),
                                        ui.tags.div(
                                            transition_label(transition),
                                            class_="student-pipeline-transition-label",
                                        ),
                                        class_="student-pipeline-transition",
                                    )
                                )

                        return ui.tags.div(
                            # ui.tags.p(
                            #     "Average time between completed milestones for active student employees.",
                            #     class_="student-pipeline-subtitle",
                            # ),
                            ui.tags.div(*flow, class_="student-pipeline-flow"),
                            # ui.tags.div(
                            #     ui.tags.span("Pipeline view", class_="student-pipeline-footer-label"),
                            #     ui.tags.span(
                            #         f"{stage_counts[-1]['completed']} of {stage_counts[0]['completed']} active students have reached CDL",
                            #         class_="student-pipeline-footer-value",
                            #     ),
                            #     class_="student-pipeline-footer",
                            # ),
                            class_="student-pipeline",
                        )

                with ui.layout_columns(col_widths=(6, 6), fill=False):
                    with ui.card(class_="dashboard-card"):
                        ui.card_header("Transition Performance Table")

                        @render.ui
                        def student_transition_performance_table():
                            table_df = student_transition_table_df()
                            if table_df.empty:
                                return ui.tags.div("No transition data available", class_="student-duration-empty")

                            body_rows = []
                            for row in table_df.to_dict('records'):
                                band_class = {
                                    'Fast': 'student-badge-fast',
                                    'On Track': 'student-badge-on-track',
                                    'Watch': 'student-badge-watch',
                                    'No data': 'student-badge-neutral',
                                }.get(row['speed_band'], 'student-badge-neutral')

                                body_rows.append(
                                    ui.tags.tr(
                                        ui.tags.td(row['transition']),
                                        ui.tags.td(
                                            f"{row['average_days']} days" if row['average_days'] is not None else 'N/A',
                                            class_="student-transition-right",
                                        ),
                                        ui.tags.td(row['range'], class_="student-transition-right"),
                                        ui.tags.td(str(row['completed']), class_="student-transition-right"),
                                        # ui.tags.td(
                                        #     ui.tags.span(row['speed_band'], class_=f"student-speed-badge {band_class}"),
                                        #     class_="student-transition-right",
                                        # ),
                                    )
                                )

                            return ui.tags.div(
                                ui.tags.table(
                                    ui.tags.thead(
                                        ui.tags.tr(
                                            ui.tags.th("Transition"),
                                            ui.tags.th("Avg Days", class_="student-transition-right"),
                                            ui.tags.th("Range", class_="student-transition-right"),
                                            ui.tags.th("Completed", class_="student-transition-right"),
                                            # ui.tags.th("Status", class_="student-transition-right"),
                                        )
                                    ),
                                    ui.tags.tbody(*body_rows),
                                    class_="student-transition-table",
                                ),
                                class_="student-transition-table-wrap",
                            )

                    with ui.card(full_screen=True, class_="dashboard-card"):
                        ui.card_header("Pipeline Bottleneck View")

                        @render_widget
                        def student_pipeline_bottleneck_chart():
                            table_df = student_transition_table_df()
                            chart_df = table_df[table_df['average_days'].notna()].copy()
                            if chart_df.empty:
                                fig = go.Figure()
                                fig.add_annotation(text="No completed transition durations", xref="paper", yref="paper", x=0.5, y=0.5)
                                fig.update_layout(height=340)
                                return fig

                            chart_df['average_days'] = chart_df['average_days'].astype(int)
                            chart_df = chart_df.sort_values('average_days', ascending=True)
                            bar_colors = [
                                '#0f766e' if value <= 7 else '#0369a1' if value <= 14 else '#b45309'
                                for value in chart_df['average_days']
                            ]

                            fig = go.Figure(
                                go.Bar(
                                    x=chart_df['average_days'],
                                    y=chart_df['transition'],
                                    orientation='h',
                                    marker_color=bar_colors,
                                    text=[f"{value} days" for value in chart_df['average_days']],
                                    textposition='outside',
                                    hovertemplate=(
                                        '<b>%{y}</b><br>'
                                        'Average: %{x} days<br>'
                                        '<extra></extra>'
                                    ),
                                )
                            )

                            fig.update_layout(
                                margin=dict(l=10, r=30, t=10, b=30),
                                xaxis_title='Average days',
                                yaxis_title=None,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                height=360,
                            )
                            fig.update_xaxes(rangemode='tozero', gridcolor='#e2e8f0')
                            fig.update_yaxes(automargin=True)
                            return fig

                