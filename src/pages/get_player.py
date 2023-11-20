import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback

dash.register_page(__name__, name="Player lookup", group="Update database")

layout = html.Div(
    [
        html.H1("Player lookup"),
        html.P(
            "Type in a player username or UUID below to save a snapshot of their" 
            " current statistics and records."
        ),
        dbc.Row(
            [
                dbc.Col(
                    [dbc.Input(id="input-user", placeholder="Username or UUID", type="text")],
                    width=12,
                    lg=6
                ),
                dbc.Col(
                    [dbc.Button("Get user data", id="get-data-btn")],
                    width=12,
                    lg=6
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Player name"),
                        html.Div("Level 123"),
                        html.Div("123,456 XP")
                    ],
                width=12, lg=3, style={"margin-bottom": "10px"}),
                dbc.Col(
                    [
                        html.Div(html.H3("TL rank")),
                        html.Div(html.Img(id="player-rank-img", src="https://tetr.io/res/league-ranks/x.png", width=40, height=40)),
                        html.Div("23434.43 TR"),
                        html.Div("R: 2323.4 \u00b1 34", style={"font-size": "0.75em"}) # plus or minus
                    ],
                    width=12, xl=2, style={"text-align": "center", "margin-bottom": "10px"}),
                dbc.Col(
                    [
                        html.Div(html.H3("TL statistics")),
                        html.Div("PPS: 2.22"),
                        html.Div("APM: 222.22"),
                        html.Div("VS: 123.45"),
                    ],
                    width=12, xl=2, style={"text-align": "center", "margin-bottom": "10px"}),
                dbc.Col(
                    [
                        html.Div(html.H3("Singleplayer records")),
                        html.Div("Sprint: 0:34:42.222"),
                        html.Div("Blitz: 1,232,232"),
                    ],
                    width=12, xl=2, style={"text-align": "center", "margin-bottom": "10px"}),
            ],
            style={"align-items": "center"}
        )
    ]
)

# html.Div(
#     [
#         html.Div(dcc.Input(id="input-on-submit", type="text")),
#         html.Button("Submit", id="submit-val", n_clicks=0),
#         html.Div(
#             id="container-button-basic", children="Enter a value and press submit"
#         ),
#     ]
# )
