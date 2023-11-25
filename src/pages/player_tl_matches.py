from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc

import sqlalchemy

import dash_reusable
import db_con
import models

dash.register_page(__name__, name="Tetra League matches", group="Player statistics")

OPTION_NONE = "(none)"

# Start by getting all players for which we have matches for
with db_con.session_maker.begin() as session:
    result = session.execute(
        sqlalchemy.select(
            models.LeagueMatchPlayer.player_id,
            sqlalchemy.func.group_concat(models.LeagueMatchPlayer.username.distinct()),
        ).group_by(models.LeagueMatchPlayer.player_id)
    ).all()
    available_players = [
        {"label": f"{usernames} ({uuid})", "value": uuid} for uuid, usernames in result
    ]

available_players.append({"label": OPTION_NONE, "value": OPTION_NONE})

layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Player match history"),
                        html.P("Select a player:"),
                        dcc.Dropdown(
                            options=available_players,
                            value=OPTION_NONE,
                            id="dropdown-players",
                            clearable=False,
                        ),
                    ],
                    width=12,
                ),
                dbc.Col([html.Div(id="output-tl-matches")], width=12),
            ]
        )
    ]
)


@callback(
    Output("output-tl-matches", "children"),
    Input("dropdown-players", "value"),
)
def update_output(uuid: str) -> html.Div:
    if uuid == OPTION_NONE:
        return html.Div("Select a user!")

    # Search for all matches with that UUID
    with db_con.session_maker.begin() as session:
        result: list[models.LeagueMatch] = session.scalars(
            sqlalchemy.select(models.LeagueMatch).join(
                models.LeagueMatchPlayer,
                sqlalchemy.and_(
                    models.LeagueMatchPlayer.tl_match_id
                    == models.LeagueMatch.replay_id,
                    models.LeagueMatchPlayer.player_id == uuid,
                ),
            )
        ).all()

        matches_table = dash_reusable.generate_match_table(result, uuid)
        rounds_table = dash_reusable.generate_round_table(result, uuid)

    return html.Div(
        [
            html.H2("Recorded matches"),
            matches_table,
            html.H2("Recorded rounds"),
            rounds_table,
        ]
    )
