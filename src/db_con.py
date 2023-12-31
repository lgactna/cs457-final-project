"""
Global database handler.

This is a global module that should be used in all interactions with the database.

By default, both the engine and the sessionmaker are initialized to None to force
the user into explicitly declaring the engine.

This also includes some various convenience methods to avoid using any database-
specific features (e.g. Postgres's "upsert", i.e. insert if not present or update)
at the cost of some performance -- for our scale, this isn't too impactful
"""
from typing import Union, Iterable

import datetime
import logging


import sqlalchemy

import models

logger = logging.getLogger(__name__)

engine: sqlalchemy.Engine = None
session_maker: sqlalchemy.orm.sessionmaker = None


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


def isolate_new_matches(matches: list[models.LeagueMatch]) -> list[models.LeagueMatch]:
    """
    Return only the matches which do not already exist in the database.
    """
    new_match_ids = set([match.replay_id for match in matches])

    with session_maker.begin() as session:
        existing = session.scalars(
            sqlalchemy.select(models.LeagueMatch).where(
                models.LeagueMatch.replay_id.in_(new_match_ids)
            )
        )
        existing_ids = set([match.replay_id for match in existing])

    surviving_ids = new_match_ids - existing_ids
    remaining = [match for match in matches if match.replay_id in surviving_ids]

    logger.debug(f"Kept {len(surviving_ids)} matches out of {len(matches)}")

    return remaining


def isolate_new_records(records: list[models.PlayerGame]) -> list[models.PlayerGame]:
    """
    Return only the singleplayer games which do not already exist in the database.
    """
    new_match_ids = set([record.replay_id for record in records])

    with session_maker.begin() as session:
        existing = session.scalars(
            sqlalchemy.select(models.PlayerGame).where(
                models.PlayerGame.replay_id.in_(new_match_ids)
            )
        )
        existing_ids = set([record.replay_id for record in existing])

    surviving_ids = new_match_ids - existing_ids
    remaining = [record for record in records if record.replay_id in surviving_ids]

    logger.debug(f"Kept {len(surviving_ids)} records out of {len(records)}")

    return remaining


def merge_records(
    lhs: list[models.PlayerGame], rhs: list[models.PlayerGame]
) -> list[models.PlayerGame]:
    """
    Merge two sets of singleplayer records, preferring those on the left.

    Adds to `lhs` in-place, and also returns it.
    """
    seen_ids = set([game.replay_id for game in lhs])
    for record in rhs:
        if record.replay_id not in seen_ids:
            seen_ids.add(record.replay_id)
            lhs.append(record)

    return lhs


def get_global_timestamps() -> list[datetime.datetime]:
    """
    Return all the available timestamps for global LeagueSnapshot instances.
    """
    with session_maker.begin() as session:
        return session.scalars(
            sqlalchemy.select(models.LeagueSnapshot.ts)
            .where(models.LeagueSnapshot.is_global)
            .distinct()
            .order_by(models.LeagueSnapshot.ts.desc())
        ).all()


def batch_create_player_objs(ids: Iterable[str]) -> None:
    """
    Instantiate and commit many player objects at once.

    This takes the IDs not already present in `ids` and creates new Player
    objects without a joindate specified.
    """
    with session_maker.begin() as session:
        # Get all players
        existing_players = set(
            session.scalars(sqlalchemy.select(models.Player.id).distinct())
        )

        # Subtract from the existing set
        new_ids: set = set(ids) - existing_players

        logger.info(f"Creating and committing {len(new_ids)} new player objects")

        # Use list comprehension to generate the relevant data and commit
        session.add_all([models.Player(id=new_id) for new_id in new_ids])
