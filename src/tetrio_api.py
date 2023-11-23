"""
Routines for grabbing and information from the TETR.IO API.

With the exception of `get_player_by_uuid`, which reads the database, none of 
these routines interact with the underlying database at all; they simply create
ORM-mapped objects that can be committed and handled by the user as needed.
"""
from typing import Union, Optional
import datetime
import logging
import time
import uuid

import dateutil
import requests
import sqlalchemy

import controller
import models
import util

logger = logging.getLogger(__name__)

API = "https://ch.tetr.io/api"

def get_player_by_uuid(uuid: str, data:Optional[dict], use_api: bool=False) -> models.Player:
    """
    Generate a player object from a UUID.
    
    This first checks the underlying database if a player already exists, and
    returns if it already exists. This *does not* commit the new player object
    to the database if one is created.
    
    By default, this simply assumes that the input UUID is valid. This is to avoid
    excessive API calls by accident, particularly when the Tetra League database is
    created for the first time.
    
    :param data: The full JSON response of an api/users/{id} call.
    """
    # Assert that this is actually a UUID
    if not util.is_valid_uuid(uuid):
        raise ValueError('A UUID is required')
    
    # Check DB by default
    if u := controller.get_player(uuid):
        return u
    
    if use_api:
        # Defer to API (or dictionary)
        if not data:
            r = requests.get(f"{API}/users/{uuid}")
            data = r.json()
            logger.debug("An API request to get a user was made. Auto-throttling.")
            time.sleep(1)
            
        if not data['success']:
            raise ValueError('User was not found')

        return models.Player(
            id=data['data']['user']['_id'],
            join_date=dateutil.parser(data['data']['user']['ts'])
        )
    
    # Trust the user and assume the UUID is good
    return models.Player(
        id=uuid
    )

def get_id_from_username(username: str, data: Optional[dict]) -> Union[str, None]:
    """
    Attempt to get the Mongo ID associated with a username.

    If the lookup fails, returns `None`.
    
    :param username: The standard username to lookup.
    """
    if not data:
        r = requests.get(f"{API}/users/{username}")
        data = r.json()

    if r['success']:
        return data["data"]["user"]["_id"]
    else:
        return None

def get_global_data(data: Optional[dict]) -> list[models.LeagueSnapshot]:
    """
    Get Tetra League snapshots for every ranked player.
    """
    if not data:
        r = requests.get(f"{API}/users/lists/league/all")
        data = r.json()
    
    ts = datetime.datetime.now(datetime.timezone.utc)
    snapshots: list[models.LeagueSnapshot] = []
    
    for rank, user in enumerate(data['data']['users'], 1):
        player = get_player_by_uuid(user['_id'])
        tl_data = user['league']
        snapshots.append(
            models.LeagueSnapshot(
                ts=ts,
                tl_games_played=tl_data['gamesplayed'],
                tl_games_won=tl_data['gameswon'],
                rating=tl_data['rating'],
                rank=tl_data['rank'],
                standing=rank, # This *should* be correct
                glicko=tl_data['glicko'],
                rd=tl_data['rd'],
                apm=tl_data['apm'],
                pps=tl_data['pps'],
                vs=tl_data['vs'],
                decaying=tl_data['decaying'],
                player=player
            )
        )
        
    return snapshots

def match_from_game(data: dict) -> models.LeagueMatch:
    """
    Interpret a Tetra League stream record into a LeagueMatch.
    """
    ts = dateutil.parser(data['ts'])
    
    match_players: List[models.LeagueMatchPlayer] = []
    for player in data['endcontext']:
        player_obj = get_player_by_uuid(player['id'])
        
        # Generate match player
        match_player_obj = models.LeagueMatchPlayer(
            winner=player['success'],
            points=player['wins'],
            arr=player['handling']['arr'],
            das=player['handling']['das'],
            dcd=player['handling']['dcd'],
            sdf=player['handling']['sdf'],
            safelock=player['handling']['safelock'],
            cancel=player['handling']['cancel'],
            username=player['username'],
            player=player_obj
        )
        
        # Generate rounds
        points = player['points']
        rounds: list[models.LeagueRound] = []
        for i in range(len(points['secondaryAvgTracking'])):
            rounds.append(models.LeagueRound(
                round_idx = i,
                apm = points['secondaryAvgTracking'][idx],
                pps = points['tertiaryAvgTracking'][idx],
                vs = points['extraAvgTracking']['aggregatestats___vsscore'][idx],
                player=player_obj,
                tl_round_player=match_player_obj
            ))
            
        # Assign rounds to player and add to set of players
        match_player_obj.rounds = rounds
        match_players.append(match_player_obj)
        
        
    # With each individual round parsed, generate the overall match structure
    return models.LeagueMatch(
        ts=ts,
        tl_players=match_players
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
    if not util.is_valid_uuid(user):
        user = get_id_from_username(user)
    
    r = requests.get(f"{API}/streams/league_userrecent_{user}")
    data = r.json()
    
    if not data['success']:
        return None
    
    # Start iterating over each game
    matches: list[models.LeagueMatch] = []
    for match_data in data['records']:
        matches.append(match_from_game(match_data))
        
    return matches


def get_player_games(user: str) -> list[models.PlayerGame]:
    """
    Get the recent Blitz and 40L games associated with the user.
    
    :param user: Either the username or user ID to get recent games for.
    :param data: If present, the dictionary to pull data from. Else, a request 
        is issued to the TETR.IO API.
    """
    pass

def get_player_records(user: str) -> list[models.PlayerGame]:
    """
    Get the current Blitz and 40L records of a user.
    
    :param user: Either the username or user ID to get singleplayer records for.
    :param data: If present, the dictionary to pull data from. Else, a request 
        is issued to the TETR.IO API.
    """
    pass

def get_player_snapshot(user: str) -> models.PlayerSnapshot:
    """
    Get a snapshot of the current user.
    """