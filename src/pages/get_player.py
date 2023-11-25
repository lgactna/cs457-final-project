import datetime
import logging

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback, dash_table

import pandas as pd

import db_con
import models
import tetrio_api

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


def generate_player_card(
    player_snapshot: models.PlayerSnapshot, tl_snapshot: models.LeagueSnapshot
) -> dbc.Row:
    """
    Generate a "player card" element from a player and TL snapshot.
    """
    # dear god lol
    tl_card_body = dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        html.Img(
                            id="player-rank-img",
                            src=f"https://tetr.io/res/league-ranks/{tl_snapshot.rank}.png",
                            width=40,
                            height=40,
                        )
                    ),
                    html.Div(f"{tl_snapshot.rating:.2f} TR"),
                    html.Div(
                        f"R: {tl_snapshot.glicko:.1f} \u00b1 {tl_snapshot.rd:.0f}",
                        style={"font-size": "0.75em"},
                    ),
                ],
                width=6,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(f"PPS: {tl_snapshot.pps:.2f}"),
                        html.Div(f"APM: {tl_snapshot.apm:.2f}"),
                        html.Div(f"VS: {tl_snapshot.vs:.2f}"),
                    ],
                    style={"text-align": "center"},
                ),
                width=6,
            ),
        ]
    )

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(player_snapshot.username),
                    html.Div(f"{player_snapshot.xp} XP"),
                    html.Div(f"{player_snapshot.games_played} games played"),
                    html.Div(f"{player_snapshot.games_won} games won"),
                    html.Div(
                        f"Time played: {str(datetime.timedelta(seconds=player_snapshot.game_time))}"
                    ),
                ],
                width=12,
                lg=4,
                style={"margin-bottom": "10px"},
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader("Tetra League"),
                            dbc.CardBody(tl_card_body),
                        ],
                        style={"height": "100%"},
                    ),
                ],
                width=12,
                xl=4,
                style={
                    "margin-bottom": "10px",
                    "text-align": "center",
                    "align-self": "stretch",
                },
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader("Other"),
                            dbc.CardBody(
                                [
                                    html.Div(f"TL wins: {tl_snapshot.tl_games_won}"),
                                    html.Div(
                                        f"TL games: {tl_snapshot.tl_games_played}"
                                    ),
                                    html.Div(
                                        f"TL winrate: {(tl_snapshot.tl_games_won/tl_snapshot.tl_games_played)*100:.2f}%"
                                    ),
                                ],
                            ),
                        ],
                        style={"height": "100%"},
                    ),
                ],
                width=12,
                xl=4,
                style={
                    "margin-bottom": "10px",
                    "text-align": "center",
                    "align-self": "stretch",
                },
            ),
        ],
        style={"align-items": "center"},
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
        games_df = pd.DataFrame([models.todict(obj) for obj in new_games])
        matches_df = pd.DataFrame([models.todict(obj) for obj in new_matches])
        player_card = generate_player_card(player_snapshot, tl_snapshot)

    # At this point, it's safe to exit the session since the data's already been
    # copied over to a dataframe

    tables = []
    for df in (games_df, matches_df):
        if len(df) == 0:
            tables.append(html.Em("No new data!"))
            continue
        tables.append(
            dash_table.DataTable(
                df.to_dict("records"),
                [{"name": i, "id": i} for i in df.columns],
                filter_action="native",
                sort_action="native",
                sort_mode="single",
                page_action="native",
                page_current=0,
                page_size=5,
            )
        )

    return html.Div(
        [
            player_card,
            dbc.Row(dbc.Col([html.H3("New singleplayer scores"), tables[0]])),
            dbc.Row(dbc.Col([html.H3("New matches"), tables[1]])),
        ]
    )
