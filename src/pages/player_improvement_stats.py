from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc
import sqlalchemy
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

import dash_reusable
import db_con
import models

dash.register_page(__name__, name="Improvement", group="Player statistics")

OPTION_NONE = "(none)"
GAMEMODE_OPTIONS = ("40l", "blitz")

# Start by getting all players for which we have games for; derive them from the
# player snapshot table (note this assumes that if we have a game for a player,
# we also have a snapshot for them -- a true statement in this application)
with db_con.session_maker.begin() as session:
    result = session.execute(
        sqlalchemy.select(
            models.PlayerGame.player_id,
            sqlalchemy.func.group_concat(models.PlayerSnapshot.username.distinct()),
        )
        .join(
            models.PlayerSnapshot,
            models.PlayerSnapshot.player_id == models.PlayerGame.player_id,
        )
        .group_by(models.PlayerGame.player_id)
    ).all()
    available_players = [
        {"label": f"{usernames} ({uuid})", "value": uuid} for uuid, usernames in result
    ]

layout = html.Div(
    [
        html.H1("Singleplayer improvement"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.P("Select a player:"),
                        dcc.Dropdown(
                            options=available_players,
                            value=OPTION_NONE,
                            id="dropdown-players",
                            clearable=False,
                        ),
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        html.P("Select a gamemode:"),
                        dcc.Dropdown(
                            options=GAMEMODE_OPTIONS,
                            value=GAMEMODE_OPTIONS[0],
                            id="dropdown-gamemode",
                            clearable=False,
                        ),
                    ],
                    width=6,
                ),
            ]
        ),
        html.Div(id="output-improvement"),
    ]
)


@callback(
    Output("output-improvement", "children"),
    Input("dropdown-players", "value"),
    Input("dropdown-gamemode", "value"),
)
def update_output(uuid: str, gamemode: str) -> html.Div:
    if uuid == OPTION_NONE:
        return html.Div("Select a user!")

    # Start by grabbing all the games associated with this UUID
    with db_con.session_maker.begin() as session:
        result: list[models.PlayerGame] = session.scalars(
            sqlalchemy.select(models.PlayerGame).where(
                models.PlayerGame.player_id == uuid,
                models.PlayerGame.gamemode == gamemode,
            )
        ).all()

        # Construct dataframe
        df = pd.DataFrame([models.todict(game) for game in result])

        # And make the table
        game_table = dash_reusable.generate_game_table(result)

    # Handle value conversions
    if gamemode == "40l":
        df["value"] = df["value"].map(lambda x: x / 1000)

    # Now construct a scatterplot just from all the game objects
    fig = px.scatter(df, x="ts", y="value")
    # Then, add an additional trace by using just the record objects
    df_records = df[df["is_record"] == True]  # noqa: E712
    fig.add_trace(go.Scatter(x=df_records["ts"], y=df_records["value"]))

    # Finish up
    return html.Div(
        [
            html.H2("Improvement chart"),
            dcc.Graph(figure=fig),
            html.H2("All associated games"),
            game_table,
        ]
    )
