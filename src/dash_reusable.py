from typing import Union
import datetime

from dash import html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

import models
import util


def generate_player_card(
    player_snapshot: models.PlayerSnapshot, tl_snapshot: models.LeagueSnapshot
) -> dbc.Row:
    """
    Generate a "player card" element from a player and TL snapshot.
    """
    if tl_snapshot.standing == -1:
        standing = html.div("(unranked)")
    else:
        standing = html.Div(f"#{tl_snapshot.standing}")

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
                    standing,
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


def generate_match_table(
    matches: list[models.LeagueMatch], focus_player: str
) -> Union[dash_table.DataTable, html.Em]:
    """
    Generate a DataTable from a set of matches.

    `focus_player` is used to determine which player should always be on the left.

    The table format is as follows:
        - player_1,
        - pts,
        - pts,
        - player_2,
        - timestamp,
        - pps (p1 | p2),
        - apm (p1 | p2),
        - vs (p1 | p2)

    If there are no matches, this simply returns a HTML element with some text.
    """
    if len(matches) == 0:
        return html.Em("No new data!")

    # We'll form a dataframe from this
    match_rows: list[dict] = []

    for match in matches:
        # First, assert that there are exactly two players for the match
        if len(match.tl_players) != 2:
            raise ValueError("TL match not comprised of two players")

        player_1: dict[str, str] = {}
        player_2: dict[str, str] = {}

        # Then, calculate statistics for each
        for player in match.tl_players:
            player_data = {}
            for field in ("pps", "apm", "vs"):
                data = [getattr(round, field) for round in player.rounds]
                player_data[field] = f"{sum(data)/len(data):.2f}"
            player_data["points"] = player.points
            player_data["username"] = player.username

            if player.username == focus_player or player.player_id == focus_player:
                player_1 = player_data
            else:
                player_2 = player_data

        # They both better be filled out here
        assert player_1 and player_2

        # Now create the actual row entry itself
        match_rows.append(
            {
                "player_1": player_1["username"],
                "p1_pts": player_1["points"],
                "p2_pts": player_2["points"],
                "player_2": player_2["username"],
                "timestamp": match.ts.strftime(util.STD_TIME_FMT),
                "pps": f"({player_1['pps']}|{player_2['pps']})",
                "apm": f"({player_1['apm']}|{player_2['apm']})",
                "vs": f"({player_1['vs']}|{player_2['vs']})",
            }
        )

    # Finally, from these, create a dataframe
    df = pd.DataFrame(match_rows)

    # And create the DataTable (pagination set at 5 for now)
    return dash_table.DataTable(
        df.to_dict("records"),
        [{"name": i, "id": i} for i in df.columns],
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        page_action="native",
        page_current=0,
        page_size=5,
    )


def generate_game_table(
    games: list[models.PlayerGame],
) -> Union[dash_table.DataTable, html.Em]:
    """
    Generate a DataTable from a set of singleplayer games.

    This also handles the conversion of milliseconds to seconds for the case of
    40L games.

    The table format is as follows:
    - gamemode
    - value
    - timestamp
    - is_player_best
    """
    if len(games) == 0:
        return html.Em("No new data!")

    game_data: list[dict] = []
    for game in games:
        value = game.value
        if game.gamemode == "40l":
            value = value / 1000

        game_data.append(
            # Just assuming the most recent username is their current --
            # this does have the interesting opportunity of allowing usernames
            # to be "tracked" and reflected over time, but we're ignoring that
            # for this project
            {
                "gamemode": game.gamemode,
                "value": value,
                "timestamp": game.ts.strftime(util.STD_TIME_FMT),
                "is_player_best": game.is_record,
            }
        )

    # Finally, from these, create a dataframe
    df = pd.DataFrame(game_data)

    # And create the DataTable (pagination set at 5 for now)
    return dash_table.DataTable(
        df.to_dict("records"),
        [{"name": i, "id": i} for i in df.columns],
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        page_action="native",
        page_current=0,
        page_size=5,
    )


def generate_round_table(
    matches: list[models.LeagueMatch], focus_player: str
) -> Union[dash_table.DataTable, html.Em]:
    """
    Generate a table of rounds, breaking matches up into their individual rounds.

    The table format is as follows:
        - player,
        - timestamp,
        - pps
        - apm
        - vs

    If there are no matches, this simply returns a HTML element with some text.
    """
    if len(matches) == 0:
        return html.Em("No new data!")

    # We'll form a dataframe from this
    round_rows: list[dict] = []

    for match in matches:
        # First, assert that there are exactly two players for the match
        if len(match.tl_players) != 2:
            raise ValueError("TL match not comprised of two players")

        # Only take the "focus" player's statistics
        for player in match.tl_players:
            if player.username != focus_player and player.player_id != focus_player:
                continue

            for round in player.rounds:
                round_rows.append(
                    {
                        "player": round.tl_round_player.username,
                        "timestamp": round.tl_round_player.tl_match.ts,
                        "pps": round.pps,
                        "apm": round.apm,
                        "vs": round.vs,
                    }
                )

    # Finally, from these, create a dataframe
    df = pd.DataFrame(round_rows)

    # And create the DataTable (pagination set at 5 for now)
    return dash_table.DataTable(
        df.to_dict("records"),
        [{"name": i, "id": i} for i in df.columns],
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        page_action="native",
        page_current=0,
        page_size=5,
    )
