"""
SQLAlchemy models for the application.

Not sure what this is actually supposed to be called for SQLAlchemy-driven
applications, but Django uses `models.py` so I guess we'll use it here too.
"""
from typing import List
from typing import Optional
import datetime
import decimal

import sqlalchemy
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

# https://stackoverflow.com/questions/54026174/proper-autogenerate-of-str-implementation-also-for-sqlalchemy-classes
# MappedAsDataclass doesn't work the way I think it does, so this is the approach
# for auto __str__ instead

def todict(obj):
    """ Return the object's dict excluding private attributes, 
    sqlalchemy state and relationship attributes.
    """
    excl = ('_sa_adapter', '_sa_instance_state')
    return {k: v for k, v in vars(obj).items() if not k.startswith('_') and
            not any(hasattr(v, a) for a in excl)}
 
class Base(DeclarativeBase):
    def __repr__(self):
        params = ', '.join(f'{k}={v}' for k, v in todict(self).items())
        return f"{self.__class__.__name__}({params})"


class Player(Base):
    """
    Permanent representation of a player.

    Usernames are *not* included here; they are considered "dynamic" and are
    part of a player snapshot. This makes it possible for player snapshots
    to be searched by username and allow the system to return all records associated
    with the underlying ID, even if the username changes over time.
    """

    __tablename__ = "player"

    # IDs in the system will be represented as pure hexadecimal strings.
    # This removes the (unnecessary) conversion layer that would need to occur if
    # we stored it as binary, since both the TETR.IO API and the user are going
    # to enter it as a hex string.
    id: Mapped[str] = mapped_column(sqlalchemy.String(24), primary_key=True)

    # This is nullable for two reasons:
    # - join dates may actually be null if not recorded
    # - players should be createable even if we don't know their join date
    join_date: Mapped[Optional[datetime.datetime]] = mapped_column(
        sqlalchemy.DateTime(), nullable=True
    )

    p_snapshots: Mapped[List["PlayerSnapshot"]] = relationship(back_populates="player")
    tl_snapshots: Mapped[List["LeagueSnapshot"]] = relationship(back_populates="player")

    p_games: Mapped[List["PlayerGame"]] = relationship(back_populates="player")
    tl_matches: Mapped[List["LeagueMatchPlayer"]] = relationship(
        back_populates="player"
    )
    tl_rounds: Mapped[List["LeagueRound"]] = relationship(back_populates="player")


class PlayerSnapshot(Base):
    """
    A snapshot of a player's non-ranked statistics at a particular point in
    time.
    """

    __tablename__ = "player_snapshot"

    # Autoincrementing serial ID.
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime.datetime] = mapped_column(sqlalchemy.DateTime())

    username: Mapped[str] = mapped_column(sqlalchemy.String(50))
    role: Mapped[str] = mapped_column(sqlalchemy.String(15))
    xp: Mapped[int] = mapped_column(sqlalchemy.Integer())
    games_played: Mapped[int] = mapped_column(sqlalchemy.Integer())
    games_won: Mapped[int] = mapped_column(sqlalchemy.Integer())
    game_time: Mapped[int] = mapped_column(sqlalchemy.Integer())
    friend_count: Mapped[int] = mapped_column(sqlalchemy.Integer())

    player: Mapped[Player] = relationship(back_populates="p_snapshots")
    player_id = mapped_column(ForeignKey("player.id"))


class PlayerGame(Base):
    """
    Represents an arbitrary game in a singleplayer mode.
    """

    __tablename__ = "player_game"

    # Autoincrementing serial ID.
    id: Mapped[int] = mapped_column(primary_key=True)

    gamemode: Mapped[str] = mapped_column(sqlalchemy.String(15))
    replay_id: Mapped[str] = mapped_column(sqlalchemy.String(24))
    ts: Mapped[datetime.datetime] = mapped_column(sqlalchemy.DateTime())
    value: Mapped[int] = mapped_column(sqlalchemy.Integer())

    # The actual numeric rank of the score on the leaderboards, if within the top
    # 1,000.
    rank: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer(), nullable=True)
    # Whether or not this is considered a coherent "record" from a singleplayer
    # perspective. Gamemode-specific.
    is_record: Mapped[bool] = mapped_column(sqlalchemy.Boolean())

    # Originally there should have been a replay file, but I realize that's
    # probably more effort than it's worth to deal with

    player: Mapped[Player] = relationship(back_populates="p_games")
    player_id = mapped_column(ForeignKey("player.id"))


class LeagueSnapshot(Base):
    """
    A snapshot of a player's Tetra League statistics at a point in time.
    """

    __tablename__ = "tl_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime.datetime] = mapped_column(sqlalchemy.DateTime())

    tl_games_played: Mapped[int] = mapped_column(sqlalchemy.Integer())
    tl_games_won: Mapped[int] = mapped_column(sqlalchemy.Integer())
    rating: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    rank: Mapped[str] = mapped_column(sqlalchemy.String(1))
    standing: Mapped[int] = mapped_column(sqlalchemy.Integer())
    glicko: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    rd: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    apm: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    pps: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    vs: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    decaying: Mapped[bool] = mapped_column(sqlalchemy.Boolean())

    player: Mapped[Player] = relationship(back_populates="tl_snapshots")
    player_id = mapped_column(ForeignKey("player.id"))


class LeagueMatch(Base):
    """
    A single "set" of Tetra League matches played between two players.

    This does not assume a strict 1v1 format, but this is currently the case.
    This should (in theory) support 1v1v1... formats if they were actually
    recorded, but it's not clear how the API will structure team-based gamemodes
    in the future.
    """

    __tablename__ = "tl_match"

    # All multiplayer games do have an internal ID associated with them (and is
    # returned with the API request), but this is maintained manually since the
    # format *could* change
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime.datetime] = mapped_column(sqlalchemy.DateTime())

    tl_players: Mapped[List["LeagueMatchPlayer"]] = relationship(
        back_populates="tl_match"
    )


class LeagueMatchPlayer(Base):
    """
    Information about a player who played in a particular Tetra League match.

    This includes handling information at the time of the match, as well as
    overall information provided by the API.
    """

    __tablename__ = "tl_match_player"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Currently "success" in API stream responses
    winner: Mapped[bool] = mapped_column(sqlalchemy.Boolean())
    points: Mapped[int] = mapped_column(sqlalchemy.Integer())

    # Handling data
    arr: Mapped[decimal.Decimal] = mapped_column(sqlalchemy.Numeric(6, 3))
    das: Mapped[decimal.Decimal] = mapped_column(sqlalchemy.Numeric(6, 3))
    dcd: Mapped[decimal.Decimal] = mapped_column(sqlalchemy.Numeric(6, 3))
    sdf: Mapped[decimal.Decimal] = mapped_column(sqlalchemy.Numeric(6, 3))
    safelock: Mapped[bool] = mapped_column(sqlalchemy.Boolean())
    cancel: Mapped[bool] = mapped_column(sqlalchemy.Boolean())

    # The username at the time of the match.
    username: Mapped[str] = mapped_column(sqlalchemy.String(50))

    # Outgoing
    tl_match: Mapped[LeagueMatch] = relationship(back_populates="tl_players")
    tl_match_id = mapped_column(ForeignKey("tl_match.id"))
    player: Mapped[Player] = relationship(back_populates="tl_matches")
    player_id = mapped_column(ForeignKey("player.id"))

    # Incoming
    rounds: Mapped[List["LeagueRound"]] = relationship(back_populates="tl_round_player")


class LeagueRound(Base):
    """
    Represents a single round played as part of a multiplyer match.

    This is not provided directly by the API, and must be calculated from
    provided information manually. Note that the "opposing" players
    are not directly stored with this object; you must take the corresponding
    round_idx of each player involved in a LeagueMatch to correlate this data.

    Additionally, note that it does not appear to be possible to derive
    the individual rounds in which a user won from the API data alone.
    This is likely tied to the underlying replay data.

    It is possible (if not likely) that these fields and how they're calculated
    will change in the future, but fortunately, not in the near future.
    """

    __tablename__ = "tl_round"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The relative round index to the LeagueMatch. This makes the currently safe
    # assumption that two players in a 1v1 will play the same number of games,
    # but falls apart if we ever get something like an open lobby of multiple
    # players, where it is not guaranteed everyone is playing at the same time.
    round_idx: Mapped[int] = mapped_column(sqlalchemy.Integer())

    apm: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    pps: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)
    vs: Mapped[Optional[float]] = mapped_column(sqlalchemy.Float(), nullable=True)

    player: Mapped[Player] = relationship(back_populates="tl_rounds")
    player_id = mapped_column(ForeignKey("player.id"))
    tl_round_player: Mapped[LeagueMatchPlayer] = relationship(back_populates="rounds")
    tl_round_player_id = mapped_column(ForeignKey("tl_match_player.id"))


def create_tables(engine: sqlalchemy.engine.Engine, checkfirst: bool = True) -> None:
    """
    Create tables for the provided engine.

    Idempotent by default; if `checkfirst = True`, tables will not be generated
    if they already exist.
    """
    Base.metadata.create_all(engine, checkfirst=checkfirst)


if __name__ == "__main__":
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)

    create_tables(engine)

    session = Session(engine)
