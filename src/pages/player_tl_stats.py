import logging

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback
import sqlalchemy
import pandas as pd
import plotly.express as px

import dash_reusable
import db_con
import models
import util

logger = logging.getLogger(__name__)

dash.register_page(__name__, name="Tetra League statistics", group="Player statistics")

layout = html.Div(
    [
        dbc.Row(
            [
                html.H1("Player historical statistics"),
                html.P("Search for a user in the database:"),
                dbc.Col(
                    [
                        dbc.Input(
                            id="input-user", placeholder="Username or UUID", type="text"
                        )
                    ],
                    width=12,
                    lg=6,
                ),
                dbc.Col(
                    [dbc.Button("Search database", id="btn-get-user")], width=12, lg=6
                ),
            ],
            style={"margin-bottom": "10px"},
        ),
        dbc.Row(dcc.Loading(id="output-data")),
    ]
)


@callback(
    Output("output-data", "children"),
    Input("btn-get-user", "n_clicks"),
    State("input-user", "value"),
    prevent_initial_call=True,
)
def get_player_data(_, user: str) -> html.Div:
    # Check if the user exists in the database; prefer uuids to usernames.
    # If a username is provided, attempt to resolve it to a UUID by poking
    # at the database.
    user = user.lower()
    with db_con.session_maker.begin() as session:
        if not util.is_valid_id(user):
            logger.info(
                f"{user} is not an ID, selecting first snapshot with that username"
            )
            snapshot: models.PlayerSnapshot = session.scalar(
                sqlalchemy.select(models.PlayerSnapshot).where(
                    models.PlayerSnapshot.username == user
                )
            )

            if not snapshot:
                return html.Div(
                    "Could not find that user; try using a UUID, or check the username."
                )

            user = snapshot.player_id

        snapshots: list[models.LeagueSnapshot] = session.scalars(
            sqlalchemy.select(models.LeagueSnapshot).where(
                models.LeagueSnapshot.player_id == user
            )
        ).all()

        if not snapshots:
            return html.Div(
                "Could not find that user; either they have no snapshots or they don't exist!"
            )

        # At this point, we now want a line graph with each distinct statistic
        # (as provided by dropdown_options) represented. This allows the user
        # to turn individual statistics on and off as desired. To do so, we
        # need a dataframe with timestamp, statistic_type, and value set,
        # then have Plotly color by statistic.
        stat_rows: list[dict[str, str]] = []

        for snapshot in snapshots:
            for var in models.LeagueSnapshot.DROPDOWN_OPTIONS:
                stat_rows.append(
                    {
                        "timestamp": snapshot.ts,
                        "stat_label": var["label"],
                        "value": getattr(snapshot, var["value"]),
                    }
                )

        # Then create a DF and figure, then place it in an object
        df = pd.DataFrame(stat_rows)
        fig = px.line(df, x="timestamp", y="value", color="stat_label")
        figure_ele = dcc.Graph(figure=fig)
        # Also create our snapshot table
        snapshot_table = dash_reusable.generate_tl_snapshot_table(snapshots)

    # Return the result
    return html.Div(
        [
            html.H2("Stats over time"),
            figure_ele,
            html.H2("Snapshot data"),
            snapshot_table,
        ]
    )
