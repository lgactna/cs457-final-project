import dash
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True)

# "Home" page largely defined through a mix of the following two:
# - https://dash-bootstrap-components.opensource.faculty.ai/examples/simple-sidebar/
# - https://dash.plotly.com/urls

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.P("TETR.IO Statistics", className="display-6"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
                for page in dash.page_registry.values()
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

# page_container is dynamically defined depending on the current page of the
# multi-page app.
content = html.Div(dash.page_container, style=CONTENT_STYLE)

app.layout = html.Div([sidebar, content])

if __name__ == "__main__":
    app.run_server(debug=True)
