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

# Separte div by groups
groups: dict[str, list] = {}
for page in dash.page_registry.values():
    group = page["group"]
    if group not in groups:
        groups[group] = []

    groups[group].append(
        dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
    )

# Generate group divs
nav_eles = []
for group_name, group_set in groups.items():
    nav_eles.append(
        html.Div([html.B(group_name), dbc.Nav(group_set, vertical=True, pills=True)])
    )

# Intersperse individual group divs with horizontal rules
# https://stackoverflow.com/questions/5920643/add-an-item-between-each-item-already-in-the-list
nv = [html.Hr()] * (len(nav_eles) * 2 - 1)
nv[0::2] = nav_eles

sidebar = html.Div(
    [html.P("TETR.IO Statistics", className="display-6"), html.Hr(), html.Div(nv)],
    style=SIDEBAR_STYLE,
)

# page_container is dynamically defined depending on the current page of the
# multi-page app.
content = html.Div(dash.page_container, style=CONTENT_STYLE)

app.layout = html.Div([sidebar, content])

if __name__ == "__main__":
    app.run_server(debug=True)
