import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback

dash.register_page(__name__, name="Tetra League statistics", group="Player statistics")

layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.H2("Current player distribution")
                )
            ]
        )
    ]
)
