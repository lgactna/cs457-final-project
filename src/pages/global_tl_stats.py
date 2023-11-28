from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly
import sqlalchemy
import pandas as pd
from dateutil import parser


import models
import db_con
import util

dash.register_page(__name__, name="Current rankwise stats", group="Global statistics")

OPTION_NONE = "(none)"
dropdown_options = models.LeagueSnapshot.DROPDOWN_OPTIONS

layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Rankwise stat distribution"),
                        dcc.Graph(id="graph-distribution"),
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.P("Rank filter"),
                        dcc.Dropdown(
                            options=[OPTION_NONE],
                            value=OPTION_NONE,
                            id="dropdown-rank-filter",
                            clearable=False,
                        ),
                    ],
                    lg=6,
                ),
                dbc.Col(
                    [
                        html.P("Timestamp"),
                        dcc.Dropdown(
                            options=[OPTION_NONE],
                            value=OPTION_NONE,
                            id="dropdown-timestamp",
                            clearable=False,
                        ),
                    ],
                    lg=6,
                ),
                dbc.Col(
                    [
                        html.P("Statistic to show"),
                        dcc.Dropdown(
                            options=dropdown_options,
                            value=dropdown_options[0]["value"],
                            id="dropdown-statistic",
                            clearable=False,
                        ),
                    ],
                    lg=6,
                ),
            ]
        ),
        html.Div(id="dummy-global-tl-stats"),
    ]
)


@callback(
    Output("dropdown-rank-filter", "options"),
    Output("dropdown-timestamp", "options"),
    Output("dropdown-timestamp", "value"),
    Input("dummy-global-tl-stats", "children"),
)
def update_rank_time_options(
    _,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    # Calculate available options for the rank and timestamp dropdowns
    with db_con.session_maker.begin() as session:
        available_times = db_con.get_global_timestamps()
        time_options = [
            {"label": val.strftime(util.STD_TIME_FMT), "value": val}
            for val in available_times
        ]

        rank_options = list(
            session.scalars(sqlalchemy.select(models.LeagueSnapshot.rank).distinct())
        )

    rank_options.append(OPTION_NONE)

    return rank_options, time_options, time_options[0]["value"]


@callback(
    Output("graph-distribution", "figure"),
    Input("dropdown-rank-filter", "value"),
    Input("dropdown-timestamp", "value"),
    Input("dropdown-statistic", "value"),
)
def update_output(
    rank_filter: str, timestamp: str, statistic: str
) -> plotly.graph_objs.Figure:
    # If no timestamp available, you can stop right there
    if timestamp == OPTION_NONE:
        df = pd.DataFrame()
        return px.histogram(df)

    # Construct query conditionally based on what's been selected
    queries = []
    if rank_filter != OPTION_NONE:
        queries.append(models.LeagueSnapshot.rank == rank_filter)

    # As far as the JS frontend is concerned, our datetime.datetime objects
    # get turned back into slightly normalized timestamps (yyyy-mm-ddThh:mm:ss),
    # so we have to convert this back into a datetime.datetime
    ts = parser.parse(timestamp)

    queries.append(models.LeagueSnapshot.ts == ts)

    with db_con.session_maker.begin() as session:
        result = session.scalars(
            sqlalchemy.select(models.LeagueSnapshot)
            .where(*queries)
            .order_by(models.LeagueSnapshot.ts)
        )

        # Note that we have to generate this in the context of the session; else,
        # all the objects we get are instantly expired
        df = pd.DataFrame([models.todict(obj) for obj in result])

    # for some reason it *only* accepts dataframes?
    fig = px.histogram(
        df, x=statistic, color_discrete_map=util.RANK_TO_COLOR, color="rank"
    )
    return fig
