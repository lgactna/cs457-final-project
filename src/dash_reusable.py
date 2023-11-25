import datetime

from dash import html
import dash_bootstrap_components as dbc

import models


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
