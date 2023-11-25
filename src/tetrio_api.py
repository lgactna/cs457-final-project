"""
Routines for grabbing and information from the TETR.IO API.

With the exception of `get_player_by_uuid`, which reads the database, none of
these routines interact with the underlying database at all; they simply create
ORM-mapped objects that can be committed and handled by the user as needed.
"""
from pathlib import Path
from typing import Optional, Union
import datetime
import json
import logging
import time

from dateutil import parser
import requests

import db_con
import models
import util

logger = logging.getLogger(__name__)

API = "https://ch.tetr.io/api"

GLOBAL_DATA_DIR = Path("./global_data").resolve()


def get_player_by_uuid(uuid: str, use_api: bool = False) -> models.Player:
    """
    Generate a player object from a UUID.

    This first checks the underlying database if a player already exists, and
    returns if it already exists. This *does* commit the new player object
    to the database if one is created.

    By default, this simply assumes that the input UUID is valid. This is to avoid
    excessive API calls by accident, particularly when the Tetra League database is
    created for the first time.

    :param data: The full JSON response of an api/users/{id} call.
    """
    # Assert that this is actually a UUID
    if not util.is_valid_id(uuid):
        raise ValueError("A UUID is required")

    # Check DB by default
    if u := db_con.get_player(uuid):
        logger.debug("Used database version of model...")
        return u

    if use_api:
        # Defer to API
        r = requests.get(f"{API}/users/{uuid}")
        data = r.json()
        logger.debug("An API request to get a user was made. Auto-throttling.")
        time.sleep(1)

        if not data["success"]:
            raise ValueError("User was not found")

        u = models.Player(
            id=data["data"]["user"]["_id"],
            join_date=parser.parse(data["data"]["user"]["ts"]),
        )

    # Trust the user and assume the UUID is good
    u = models.Player(id=uuid)

    # Auto-commit the new player, so that any successive operations will use
    # the stored player object instead of creating new ones
    with db_con.session_maker.begin() as session:
        logger.debug("Created and committed new model...")
        session.add(u)

    return u


def get_id_from_username(username: str) -> Union[str, None]:
    """
    Attempt to get the Mongo ID associated with a username.

    If the lookup fails, returns `None`.

    :param username: The standard username to lookup.
    """
    # Always convert to lowercase.
    username = username.lower()

    r = requests.get(f"{API}/users/{username}")
    data = r.json()

    if data["success"]:
        return data["data"]["user"]["_id"]
    else:
        return None


def get_global_data(
    data: dict,
    *,
    preset_ts: Optional[datetime.datetime] = None,
    out_dir: Path = GLOBAL_DATA_DIR,
) -> list[models.LeagueSnapshot]:
    """
    Get Tetra League snapshots for every ranked player.

    Explicitly specify an empty dictionary for `data` if necessary. During
    development, you should aim to use a stored copy of the global data where
    needed.
    """
    if preset_ts:
        ts = preset_ts
    else:
        ts = datetime.datetime.now(datetime.timezone.utc)

    if not data:
        # TODO: Still gotta see if this actually works, stopped testing since
        # I've hit this like five times already

        # Test if this should be allowed at all. Note that the timestamps in the
        # database have no timezone information, so we have to strip that off
        # as well.
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        if ts in db_con.get_global_timestamps():
            logger.error(
                "There already exists global data for today in the database - returning an empty list!"
            )
            return []

        logger.warning(
            "Generating API request for the global TL dump! Stalling for ten seconds."
        )
        time.sleep(10)
        r = requests.get(f"{API}/users/lists/league/all")
        data = r.json()

        # Save the contents of the response out to a JSON file as needed
        name = ts.strftime("global-%Y-%m-%d.json")
        target = out_dir / name
        logger.info(f"Writing received JSON as {target}")
        with open(target, "w+") as fp:
            fp.write(r.text)

    snapshots: list[models.LeagueSnapshot] = []

    for rank, user in enumerate(data["data"]["users"], 1):
        # We don't use the `player` relationship here to avoid the weird
        # out-of-session reconciliation that would need to happen otherwise.
        # player = get_player_by_uuid(user["_id"])
        tl_data = user["league"]
        snapshots.append(
            models.LeagueSnapshot(
                ts=ts,
                tl_games_played=tl_data["gamesplayed"],
                tl_games_won=tl_data["gameswon"],
                rating=tl_data["rating"],
                rank=tl_data["rank"],
                standing=rank,  # This *should* be correct
                glicko=tl_data["glicko"] if "glicko" in tl_data else None,
                rd=tl_data["rd"] if "rd" in tl_data else None,
                apm=tl_data["apm"] if "apm" in tl_data else None,
                pps=tl_data["pps"] if "pps" in tl_data else None,
                vs=tl_data["vs"] if "vs" in tl_data else None,
                decaying=tl_data["decaying"],
                player_id=user["_id"],
                is_global=True,
            )
        )

    return snapshots


def regenerate_global_data(data_dir: Path) -> list[models.LeagueSnapshot]:
    """
    Regenerate the global data captures from a directory of JSON dumps. The
    file format is required to be "global-yyyy-mm-dd.json".

    If the associated timestamp is already present in the database, this does
    nothing for that file.

    Returns a list of LeagueSnapshot instances that are *unlikely* to already
    be in the database based on their timestamp.
    """
    logger.debug(f"Attempting to regenerate global data from {data_dir}")

    # First, get all the unique timestamps already present; only take "global"
    # snapshots
    snapshots: list[models.LeagueSnapshot] = []

    existing_times = db_con.get_global_timestamps()

    # Then, iterate over each file and check if it's already in the database.
    # If not, add the data it contains.
    for file in data_dir.glob("**/*"):
        if not file.is_file():
            logger.debug(f"Skipping {file}, is a directory")
            continue

        try:
            ts = datetime.datetime.strptime(file.name, "global-%Y-%m-%d.json")
        except ValueError:
            logger.debug(f"Skipping {file}, does not match required format")
            continue

        if ts in existing_times:
            logger.debug(
                f"Skipping {file}, data at timestamp already exists in database"
            )
            continue

        logger.info(f"Importing data from {file}")
        with open(file) as fp:
            snapshots += get_global_data(json.load(fp), preset_ts=ts)

    return snapshots


def match_from_game(data: dict) -> models.LeagueMatch:
    """
    Interpret a Tetra League stream record into a LeagueMatch.
    """
    ts = parser.parse(data["ts"])

    match_players: list[models.LeagueMatchPlayer] = []
    for player in data["endcontext"]:
        # player_obj = get_player_by_uuid(player["id"])

        # Generate match player
        match_player_obj = models.LeagueMatchPlayer(
            winner=player["success"],
            points=player["wins"],
            arr=player["handling"]["arr"],
            das=player["handling"]["das"],
            dcd=player["handling"]["dcd"],
            sdf=player["handling"]["sdf"],
            safelock=player["handling"]["safelock"],
            cancel=player["handling"]["cancel"],
            username=player["username"],
            player_id=player["id"],
        )

        # Generate rounds
        points = player["points"]
        rounds: list[models.LeagueRound] = []
        for idx in range(len(points["secondaryAvgTracking"])):
            rounds.append(
                models.LeagueRound(
                    round_idx=idx,
                    apm=points["secondaryAvgTracking"][idx],
                    pps=points["tertiaryAvgTracking"][idx],
                    vs=points["extraAvgTracking"]["aggregatestats___vsscore"][idx],
                    player_id=player["id"],
                    tl_round_player=match_player_obj,
                )
            )

        # Assign rounds to player and add to set of players
        match_player_obj.rounds = rounds
        match_players.append(match_player_obj)

    # With each individual round parsed, generate the overall match structure
    return models.LeagueMatch(
        replay_id=data["replayid"], ts=ts, tl_players=match_players
    )


def get_player_matches(user: str) -> Union[list[models.LeagueMatch], None]:
    """
    Get the recent Tetra League matches associated with the user.

    This also generates the `LeagueMatchPlayer` and `LeagueRound` information
    associated with the match.

    Returns `None` if the player does not exist. Note that an empty
    list is returned in all other cases, including if the player
    has not played any games recently or is banned.

    :param user: Either the username or user ID to get matches for.
    """
    # We need a UUID to inspect the stream. Assume that if a conversion fails,
    # it must be because this is not a UUID.
    if not util.is_valid_id(user):
        u = get_id_from_username(user)
        if not u:
            return None
        user = u

    r = requests.get(f"{API}/streams/league_userrecent_{user}")
    data = r.json()

    if not data["success"]:
        return None

    # Start iterating over each game
    matches: list[models.LeagueMatch] = []
    for match_data in data["data"]["records"]:
        matches.append(match_from_game(match_data))

    return matches


def parse_record(game: dict, player_id: str) -> models.PlayerGame:
    """
    Parse a singleplayer record.

    You must generate the affiliated player object ahead of time.
    """
    gamemode = game["endcontext"]["gametype"]
    if gamemode == "40l":
        value = game["endcontext"]["finalTime"]
    elif gamemode == "blitz":
        value = game["endcontext"]["score"]
    else:
        raise RuntimeError(f"Unknown gamemode {gamemode}")

    return models.PlayerGame(
        gamemode=gamemode,
        replay_id=game["replayid"],
        ts=parser.parse(game["ts"]),
        value=value,
        is_record=False,  # By default
        player_id=player_id,
    )


def get_player_recent(user: str) -> Union[list[models.PlayerGame], None]:
    """
    Get the recent Blitz and 40L games associated with the user.

    :param user: Either the username or user ID to get recent games for.
    """
    # We need a UUID to inspect the stream. Assume that if a conversion fails,
    # it must be because this is not a UUID.
    if not util.is_valid_id(user):
        u = get_id_from_username(user)
        if not u:
            return None
        user = u

    r = requests.get(f"{API}/streams/any_userrecent_{user}")
    data = r.json()

    if not data["success"]:
        return None

    # player_obj = get_player_by_uuid(user, use_api=True)

    games: list[models.PlayerGame] = []
    for game in data["data"]["records"]:
        games.append(parse_record(game, user))

    return games


def get_player_records(user: str) -> Union[list[models.PlayerGame], None]:  # type: ignore
    """
    Get the current Blitz and 40L records of a user. This amounts
    to the top n records for that user, typically the top 10, for
    the two gamemodes.

    :param user: Either the username or user ID to get singleplayer records for.
    """
    # We need a UUID to inspect the stream. Assume that if a conversion fails,
    # it must be because this is not a UUID.
    if not util.is_valid_id(user):
        u = get_id_from_username(user)
        if not u:
            return None
        user = u

    r = requests.get(f"{API}/streams/league_userrecent_{user}")
    data = r.json()

    # All raw records
    raw_records: list[dict] = []

    # Make API for Blitz scores
    r = requests.get(f"{API}/streams/blitz_userbest_{user}")
    data = r.json()
    if not data["success"]:
        return None

    # Exclude the first (which is guaranteed to get caught by the next req)
    if data["data"]["records"]:
        raw_records += data["data"]["records"][1:]

    # Make API for 40L scores
    r = requests.get(f"{API}/streams/40l_userbest_{user}")
    data = r.json()
    if not data["success"]:
        return None

    # Again, exclude the first
    if data["data"]["records"]:
        raw_records += data["data"]["records"][1:]

    # player_obj = get_player_by_uuid(user, use_api=True)
    games: list[models.PlayerGame] = []
    for game in raw_records:
        games.append(parse_record(game, user))

    # Make API call for the user's actual records, which contain slightly more
    # information
    r = requests.get(f"{API}/users/{user}/records")
    data = r.json()
    if not data["success"]:
        return None

    for gamemode_record in data["data"]["records"].values():
        if not gamemode_record["record"]:
            # The API always returns a key for 40L and Blitz, even if a player
            # has never played that mode
            continue

        game_obj: models.PlayerGame = parse_record(gamemode_record["record"], user)
        game_obj.rank = gamemode_record["rank"]
        game_obj.is_record = True
        games.append(game_obj)

    return games


def get_player_snapshots(
    user: str,  # type: ignore
) -> Union[tuple[models.PlayerSnapshot, models.LeagueSnapshot], None]:
    """
    Get a TL and player snapshot of the current user.

    Strictly speaking, this is designed to get PlayerSnapshot instances; however,
    since LeagueSnapshots can also be constructed from the same data, and there
    is virtually no chance of the snapshot overlapping in time from a global
    pull, a LeagueSnapshot is also provided.
    """
    r = requests.get(f"{API}/users/{user}")
    data = r.json()

    if not data["success"]:
        return None

    p_data = data["data"]["user"]
    # player_obj = get_player_by_uuid(p_data["_id"])

    p_snapshot = models.PlayerSnapshot(
        ts=datetime.datetime.now(datetime.timezone.utc),
        username=p_data["username"],
        xp=int(p_data["xp"]),
        games_played=p_data["gamesplayed"],
        games_won=p_data["gameswon"],
        game_time=int(p_data["gametime"]),
        friend_count=p_data["friend_count"],
        player_id=p_data["_id"],
    )

    # This is always present, even if the user's never
    # played anything
    tl_data = p_data["league"]
    tl_snapshot = models.LeagueSnapshot(
        ts=datetime.datetime.now(datetime.timezone.utc),
        tl_games_played=tl_data["gamesplayed"],
        tl_games_won=tl_data["gameswon"],
        rating=tl_data["rating"],
        rank=tl_data["rank"],
        standing=tl_data["standing"],
        glicko=tl_data["glicko"] if "glicko" in tl_data else None,
        rd=tl_data["rd"] if "rd" in tl_data else None,
        apm=tl_data["apm"] if "apm" in tl_data else None,
        pps=tl_data["pps"] if "pps" in tl_data else None,
        vs=tl_data["vs"] if "vs" in tl_data else None,
        decaying=tl_data["decaying"],
    )

    return (p_snapshot, tl_snapshot)
