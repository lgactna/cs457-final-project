"""
Global database handler.

This is a global module that should be used in all interactions with the database.

By default, both the engine and the sessionmaker are initialized to None to force
the user into explicitly declaring the engine.
"""
from typing import Optional, Union

import sqlalchemy

import models

engine: Optional[sqlalchemy.Engine] = None
session_maker: Optional[sqlalchemy.orm.sessionmaker] = None


def init_engine(url: str, echo: bool = True) -> None:
    """
    Initialize the global module states.
    """
    global engine
    global session_maker
    engine = sqlalchemy.create_engine(url, echo=echo)
    session_maker = sqlalchemy.orm.sessionmaker(engine)


def get_player(uuid: str) -> Union[models.Player, None]:
    """
    Get a player by UUID.

    If the player does not exist, returns None.
    """
    with session_maker.begin() as session:
        return session.scalar(
            sqlalchemy.select(models.Player).where(models.Player.id == uuid)
        )
