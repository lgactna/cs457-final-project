import datetime

from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly
import sqlalchemy
import pandas as pd


import models
import db_con
import util

dash.register_page(__name__, name="Historical averages", group="Global statistics")

dropdown_options = models.LeagueSnapshot.DROPDOWN_OPTIONS

layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Global averages over time"),
                        dcc.Graph(id="graph-timestats"),
                    ]
                )
            ]
        ),
        dbc.Row(
            [
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
    ]
)


@callback(
    Output("graph-timestats", "figure"),
    Input("dropdown-statistic", "value"),
)
def update_output(statistic: str) -> plotly.graph_objs.Figure:
    with db_con.session_maker.begin() as session:
        result: tuple[datetime.datetime, str, float] = session.execute(
            sqlalchemy.select(
                models.LeagueSnapshot.ts,
                models.LeagueSnapshot.rank,
                sqlalchemy.func.avg(getattr(models.LeagueSnapshot, statistic)),
            )
            .where(models.LeagueSnapshot.is_global)
            .group_by(models.LeagueSnapshot.ts, models.LeagueSnapshot.rank)
        ).all()
        
        if not result:
            # In the case there's no data.
            df = pd.DataFrame()
            return px.line(df)

        df = pd.DataFrame(result, columns=["timestamp", "rank", "average"])
        # Note that we have to generate this in the context of the session; else,
        # all the objects we get are instantly expired
        # df = pd.DataFrame([models.todict(obj) for obj in result])

    # for some reason it *only* accepts dataframes?
    fig = px.line(
        df,
        x="timestamp",
        y="average",
        color_discrete_map=util.RANK_TO_COLOR,
        color="rank",
    )
    return fig
