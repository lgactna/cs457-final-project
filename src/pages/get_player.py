import logging

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback, dash_table

import pandas as pd

import db_con
import models
import tetrio_api
import dash_reusable

logger = logging.getLogger(__name__)

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
                    [
                        dbc.Input(
                            id="input-user", placeholder="Username or UUID", type="text"
                        )
                    ],
                    width=12,
                    lg=6,
                ),
                dbc.Col(
                    [dbc.Button("Get user data", id="btn-get-data")], width=12, lg=6
                ),
            ],
            style={"margin-bottom": "10px"},
        ),
        dcc.Loading(html.Div(id="output-lookup")),
    ]
)


@callback(
    Output("output-lookup", "children"),
    Input("btn-get-data", "n_clicks"),
    State("input-user", "value"),
    prevent_initial_call=True,
)
def get_player_data(_, user: str) -> html.Div:
    # Check if the user exists
    uuid = tetrio_api.get_id_from_username(user)
    if uuid is None:
        return [dcc.Markdown("**Lookup failed:** this user doesn't seem to exist!")] * 2

    # If this succeeds, assume all successive lookups will succeed.
    # Wrap everything in a session so that things don't explode
    with db_con.session_maker.begin() as session:
        # Get all relevant data
        player_snapshot, tl_snapshot = tetrio_api.get_player_snapshots(uuid)
        recent_games = tetrio_api.get_player_recent(uuid)
        record_games = tetrio_api.get_player_records(uuid)
        matches = tetrio_api.get_player_matches(uuid)

        # Also implicitly create the player
        tetrio_api.get_player_by_uuid(uuid)

        # Merge the recent games, preferring records over recents if they conflict
        all_games = db_con.merge_records(record_games, recent_games)

        # Check the database if any of these "new" elements exist
        new_games = db_con.isolate_new_records(all_games)
        new_matches = db_con.isolate_new_matches(matches)

        session.add(player_snapshot)
        session.add(tl_snapshot)
        session.add_all(new_games)
        session.add_all(new_matches)

        # With the data, generate elements as needed
        game_table = dash_reusable.generate_game_table(new_games)
        matches_table = dash_reusable.generate_match_table(new_matches, uuid)
        player_card = dash_reusable.generate_player_card(player_snapshot, tl_snapshot)

    # At this point, it's safe to exit the session since the data's already been
    # copied

    return html.Div(
        [
            player_card,
            dbc.Row(dbc.Col([html.H3("New singleplayer scores"), game_table])),
            dbc.Row(dbc.Col([html.H3("New matches"), matches_table])),
        ]
    )
