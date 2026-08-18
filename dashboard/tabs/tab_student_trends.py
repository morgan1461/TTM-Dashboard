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
        ui.h4("Student Training Timeline")
        ui.p("Average progression from orientation through permit, DOT certification, CDL training, and final CDL completion. Permit deadlines are shown as a benchmark for timing risk.")

        @reactive.calc
        def student_snapshot_df():
            df = student_trends_df.copy()
            df = df[df['active'] == 1].copy()

            for col in [
                'orientation_date',
                'student_permit_deadline',
                'student_cdl_permit_date',
                'cdl_training_start_date',
                'student_cdl_date',
            ]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            return df

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

            valid = df.dropna(subset=['orientation_date', 'student_cdl_permit_date', 'cdl_training_start_date', 'student_cdl_date']).copy()
            if valid.empty:
                return {
                    'labels': [],
                    'days': [],
                    'intervals': {},
                    'deadline_days': None,
                    'total_days': 0,
                }

            valid['orientation_to_permit'] = (valid['student_cdl_permit_date'] - valid['orientation_date']).dt.days
            valid['permit_to_dot'] = (valid['cdl_training_start_date'] - valid['student_cdl_permit_date']).dt.days
            valid['dot_to_training'] = (valid['cdl_training_start_date'] - valid['student_cdl_permit_date']).dt.days
            valid['training_to_cdl'] = (valid['student_cdl_date'] - valid['cdl_training_start_date']).dt.days

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

        with ui.layout_column_wrap(fill=False):
            with ui.value_box(showcase=icon_svg("user-graduate").add_style(f"fill: {STUDENT_COLOR} !important;")):
                "Active Students"
                @render.ui
                def active_students_kpi():
                    df_f = student_snapshot_df()
                    if df_f.empty:
                        return ui.tags.div(ui.tags.span("0", class_="kpi-current"))
                    return ui.tags.div(ui.tags.span(str(int(df_f.shape[0])), class_="kpi-current"))

            with ui.value_box(showcase=icon_svg("id-card").add_style(f"fill: {STUDENT_NON_CDL_COLOR} !important;")):
                "Avg. Orientation -> Permit"
                @render.ui
                def permit_timing_kpi():
                    metrics = student_timeline_metrics()
                    interval = metrics['intervals'].get('orientation_to_permit')
                    if interval is None or pd.isna(interval):
                        return ui.tags.div(ui.tags.span("N/A", class_="kpi-current"))
                    val = int(round(interval))
                    return ui.tags.div(
                        ui.tags.span(f"{val} days", class_="kpi-current"),
                        ui.tags.span(" average", style="font-size: 0.8rem; color: #64748b; margin-left: 0.25rem;"),
                    )

            with ui.value_box(showcase=icon_svg("truck").add_style(f"fill: {STUDENT_CDL_COLOR} !important;")):
                "Avg. Training -> CDL"
                @render.ui
                def training_to_cdl_kpi():
                    metrics = student_timeline_metrics()
                    interval = metrics['intervals'].get('training_to_cdl')
                    if interval is None or pd.isna(interval):
                        return ui.tags.div(ui.tags.span("N/A", class_="kpi-current"))
                    val = int(round(interval))
                    return ui.tags.div(
                        ui.tags.span(f"{val} days", class_="kpi-current"),
                        ui.tags.span(" average", style="font-size: 0.8rem; color: #64748b; margin-left: 0.25rem;"),
                    )

        with ui.card(full_screen=True):
            ui.card_header("Average Student Progression Timeline TEST 1234")
            @render_widget
            def student_progress_timeline_chart():
                metrics = student_timeline_metrics()
                if not metrics['labels']:
                    fig = go.Figure()
                    fig.add_annotation(text="No milestone data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                    fig.update_layout(height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    return fig

                labels = metrics['labels']
                x_vals = metrics['days']
                colors = [
                    STUDENT_COLOR,
                    STUDENT_NON_CDL_COLOR,
                    '#2563EB',
                    STUDENT_TRAINING_CDL_COLOR,
                    STUDENT_CDL_COLOR,
                ]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=[0, 0, 0, 0, 0],
                    mode='lines+markers+text',
                    line=dict(color='#334155', width=2),
                    marker=dict(size=15, color=colors),
                    text=[f"{int(round(v))}d" for v in x_vals],
                    textposition=['top center', 'top center', 'top center', 'top center', 'top center'],
                    hovertemplate='%{text}<extra></extra>',
                ))

                for value, label, color in zip(x_vals, labels, colors):
                    fig.add_annotation(
                        x=value,
                        y=0,
                        text=label,
                        showarrow=False,
                        yshift=18,
                        font=dict(size=11, color='#0F172A'),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor=color,
                        borderwidth=1,
                        align='center',
                    )

                if metrics['deadline_days'] is not None:
                    fig.add_vline(
                        x=metrics['deadline_days'],
                        line_dash='dash',
                        line_color='#DC2626',
                        annotation_text='Permit deadline',
                        annotation_position='top left',
                    )

                fig.update_layout(
                    title='Average days by milestone',
                    template='plotly_white',
                    margin=dict(l=20, r=20, t=46, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=360,
                    showlegend=False,
                    xaxis_title='Days from orientation',
                    yaxis=dict(showgrid=False, zeroline=False, visible=False),
                    font=dict(size=12, color='#334155'),
                )

                if metrics['total_days'] > 0:
                    fig.update_xaxes(range=[0, max(metrics['total_days'] * 1.25, 30)])

                return fig
