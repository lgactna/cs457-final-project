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

layout = html.Div(
    [
        html.H1("Singleplayer improvement"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.P("Select a player:"),
                        dcc.Dropdown(
                            options=[OPTION_NONE],
                            value=OPTION_NONE,
                            id="dropdown-players-improvement",
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
                            id="dropdown-gamemode-improvement",
                            clearable=False,
                        ),
                    ],
                    width=6,
                ),
            ]
        ),
        html.Div(id="output-improvement"),
        html.Div(id="dummy-improvement"),
    ]
)


# There are two generally accepted methods of forcing a layout update on page
# load -- either you can set the layout to be evaluated as a function that returns
# a layout (so that the entire layout is regenerated each time as needed), or
# you can create a callback with a "dummy" input hooked up to something that
# will never do anything, and discard the input.
#
# Because there is a *possibility* that this takes an extended amount of time,
# I opted to take the approach of building blank callbacks.
@callback(
    Output("dropdown-players-improvement", "options"),
    Input("dummy-improvement", "children"),
)
def update_player_options(_) -> list[dict[str, str]]:
    # Start by getting all players for which we have games for; derive them from the
    # player snapshot table (note this assumes that if we have a game for a player,
    # we also have a snapshot for them -- a true statement in this application)
    with db_con.session_maker.begin() as session:
        result: list[tuple[str, str]] = session.execute(
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
            {"label": f"{usernames} ({uuid})", "value": uuid}
            for uuid, usernames in result
        ]

    # Also tack on the option of "nothing"
    available_players.append({"label": OPTION_NONE, "value": OPTION_NONE})
    return available_players


@callback(
    Output("output-improvement", "children"),
    Input("dropdown-players-improvement", "value"),
    Input("dropdown-gamemode-improvement", "value"),
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
    fig.add_trace(go.Scatter(x=df_records["ts"], y=df_records["value"], name="Records"))

    # Finish up
    return html.Div(
        [
            html.H2("Improvement chart"),
            dcc.Graph(figure=fig),
            html.H2("All associated games"),
            game_table,
        ]
    )
