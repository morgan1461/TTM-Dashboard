'''
TTM Dashboard
Author: Clay Morgan (Morgan.1461)
Last Edited: 2026-7-23
'''
from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_widget, render_plotly
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# pull data for dashboard concept from fake data gen
df = pd.read_csv("test_data.csv")

with ui.layout_columns():
    @render_plotly
    def plot():
        fig = px.line(df, x="Date", y="Value", title="Sample Line Plot")
        return fig

with ui.layout_columns():
    ui.input_seelct("var1", None, choices=[''])