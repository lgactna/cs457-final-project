import dash
from dash import html

dash.register_page(__name__, name="Tetra League matches", group="Player statistics")

layout = html.Div(
    [
        html.H1("This is our Home page"),
        html.Div("This is our Home page content."),
    ]
)