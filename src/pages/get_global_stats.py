import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, callback

# This is registered as the homepage with path `/`, else accessing the server
# yields a 404 until you click on one of the pages
dash.register_page(
    __name__, path="/", name="Get global statistics", group="Update database"
)

layout = html.Div(
    [
        html.H1("Get global statistics"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.P(
                            "Use this to update the global ranked player statistics. You are limited"
                            " to retrieving this information once per day based on the most recent"
                            " timestamps available in the databse. Unranked players are not included."
                            " This will take about two minutes - be patient!"
                        ),
                        dbc.Button(
                            "Request global statistics",
                            id="request-global-update-btn",
                            style={"margin-bottom": "10px"},
                        ),
                    ],
                    width=12,
                ),
                dbc.Col(
                    [
                        html.B("Request results will appear below."),
                        dbc.Spinner(html.Div(id="request-result")),
                    ],
                    width=12,
                ),
            ]
        ),
    ]
)


@callback(
    Output("request-result", "children"),
    Input("request-global-update-btn", "n_clicks"),
    prevent_initial_call=True,
)
def update_output(_) -> str:
    import time

    time.sleep(1)
    return "Update requested."
