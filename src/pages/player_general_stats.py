from typing import Union
import datetime
import logging

from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import sqlalchemy

import dash_reusable
import db_con
import util
import models

logger = logging.getLogger(__name__)

dash.register_page(__name__, name="General", group="Player statistics")

OPTION_NONE = "(none)"

layout = html.Div(
    [
        html.H1("Player overview"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.P("Select a player:"),
                        dcc.Dropdown(
                            options=[OPTION_NONE],
                            value=OPTION_NONE,
                            id="dropdown-player-overview",
                            clearable=False,
                        ),
                    ],
                    lg=6,
                ),
                dbc.Col(
                    [
                        html.P("Timestamp (player card)"),
                        dcc.Dropdown(
                            options=[OPTION_NONE],
                            value=OPTION_NONE,
                            id="dropdown-timestamp-overview",
                            clearable=False,
                        ),
                    ],
                    lg=6,
                ),
            ]
        ),
        dcc.Loading(id="output-player-card"),
        dcc.Loading(id="output-stats-and-snapshots"),
        html.Div(id="dummy-general-stats"),
    ]
)


@callback(
    Output("dropdown-player-overview", "options"),
    Input("dummy-general-stats", "children"),
)
def update_player_options(_) -> list[dict[str, str]]:
    # Get all players for which we have a snapshot
    with db_con.session_maker.begin() as session:
        result: list[tuple[str, str]] = session.execute(
            sqlalchemy.select(
                models.PlayerSnapshot.player_id,
                sqlalchemy.func.group_concat(models.PlayerSnapshot.username.distinct()),
            ).group_by(models.PlayerSnapshot.player_id)
        ).all()
        available_players = [
            {"label": f"{usernames} ({uuid})", "value": uuid}
            for uuid, usernames in result
        ]

    # Also tack on the option of "nothing"
    available_players.append({"label": OPTION_NONE, "value": OPTION_NONE})
    return available_players


@callback(
    Output("dropdown-timestamp-overview", "options"),
    Output("dropdown-timestamp-overview", "value"),
    Input("dropdown-player-overview", "value"),
)
def update_available_snapshots(uuid: str) -> tuple[list[dict[str, str]], str]:
    if uuid == OPTION_NONE:
        return [{"label": OPTION_NONE, "value": OPTION_NONE}], OPTION_NONE

    # Calculate available options for the rank and timestamp dropdowns
    # Store the actual snapshot ID as the value so we don't have to go hunt it
    # down later
    with db_con.session_maker.begin() as session:
        available_times: list[tuple[datetime.datetime, int]] = session.execute(
            sqlalchemy.select(models.PlayerSnapshot.ts, models.PlayerSnapshot.id)
            .where(models.PlayerSnapshot.player_id == uuid)
            .order_by(models.PlayerSnapshot.ts.desc())
        ).all()

        time_options = [
            {"label": val[0].strftime(util.STD_TIME_FMT), "value": str(val[1])}
            for val in available_times
        ]

    return time_options, time_options[0]["value"]


@callback(
    Output("output-player-card", "children"),
    Input("dropdown-timestamp-overview", "value"),
)
def update_player_card(id: str) -> Union[html.Div, dbc.Row]:
    if id == OPTION_NONE:
        return html.Div()

    with db_con.session_maker.begin() as session:
        snapshots: tuple[
            models.PlayerSnapshot, models.LeagueSnapshot
        ] = session.execute(
            sqlalchemy.select(models.PlayerSnapshot, models.LeagueSnapshot)
            .where(models.PlayerSnapshot.id == id)
            .join(
                models.LeagueSnapshot,
                sqlalchemy.and_(
                    models.LeagueSnapshot.player_id == models.PlayerSnapshot.player_id,
                    models.LeagueSnapshot.ts == models.PlayerSnapshot.ts,
                ),
            )
        ).one_or_none()

        if not snapshots:
            logger.error(f"Failed to find associated snapshot for {id=}")
            return html.Div(
                "Didn't find associated snapshot - this is a programming error!"
            )

        return dash_reusable.generate_player_card(*snapshots)


@callback(
    Output("output-stats-and-snapshots", "children"),
    Input("dropdown-player-overview", "value"),
)
def update_stats_and_snapshots(uuid: str) -> html.Div:
    if uuid == OPTION_NONE:
        return html.Div()

    with db_con.session_maker.begin() as session:
        snapshots: list[models.PlayerSnapshot] = session.scalars(
            sqlalchemy.select(models.PlayerSnapshot).where(
                models.PlayerSnapshot.player_id == uuid
            )
        ).all()

        if not snapshots:
            logger.error(f"Failed to find snapshots for {uuid=}")
            return html.Div("Didn't find any snapshots - this is a programming error!")

        # See player_tl_stats.py for the approach taken here
        stat_rows: list[dict[str, str]] = []

        for snapshot in snapshots:
            for var in models.PlayerSnapshot.DROPDOWN_OPTIONS:
                stat_rows.append(
                    {
                        "timestamp": snapshot.ts,
                        "stat_label": var["label"],
                        "value": getattr(snapshot, var["value"]),
                    }
                )

        df = pd.DataFrame(stat_rows)
        fig = px.line(df, x="timestamp", y="value", color="stat_label")
        figure_ele = dcc.Graph(figure=fig)

        # And create the snapshot table
        snapshot_table = dash_reusable.generate_player_snapshot_table(snapshots)

    # Generate and return the result
    return html.Div(
        [
            html.H2("Stats over time"),
            figure_ele,
            html.H2("Snapshot data"),
            snapshot_table,
        ]
    )
