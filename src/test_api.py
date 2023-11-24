"""
Various testing routines to make sure the API works
"""
import db_con
import models
import tetrio_api

import json
import sys
import logging
import pandas as pd
import sqlalchemy
from dateutil import parser

logging.basicConfig(
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# Test that everything works
# controller.init_engine('sqlite+pysqlite:///:memory:', echo=False)
db_con.init_engine("sqlite:///tetrio.db", echo=False)
models.create_tables(db_con.engine)

with db_con.session_maker.begin() as session:
    available_times = list(
        session.scalars(sqlalchemy.select(models.LeagueSnapshot.ts).distinct())
    )
    print(available_times)
    x = list(
        session.scalars(
            sqlalchemy.select(models.LeagueSnapshot).where(
                models.LeagueSnapshot.player_id == "5e7143c90f031003f4393fbf"
            )
        )
    )
    # print(x)

# with open('global_data/global-2023-11-14.json') as fp:
#     data = json.load(fp)

# g_data = tetrio_api.get_global_data(data)
# for obj in g_data:
#     obj.ts = parser.parse('2023-11-14T23:48:00.000Z')

# with db_con.session_maker.begin() as session:
#     session.add_all(g_data)

# with open('global_data/global-2023-11-24.json') as fp:
#     data = json.load(fp)

# g_data = tetrio_api.get_global_data(data)
# with db_con.session_maker.begin() as session:
#     session.add_all(g_data)

exit()

player_snapshot, tl_snapshot = tetrio_api.get_player_snapshots("kisun")

# print(player_snapshot)
# print(tl_snapshot)
uuid = "5e7143c90f031003f4393fbf"

recent_games = tetrio_api.get_player_recent(uuid)
record_games = tetrio_api.get_player_records(uuid)

all_games = db_con.merge_records(record_games, recent_games)

matches = tetrio_api.get_player_matches(uuid)

all_games = db_con.isolate_new_records(all_games)
matches = db_con.isolate_new_matches(matches)

with db_con.session_maker.begin() as session:
    session.add(player_snapshot)
    session.add(tl_snapshot)
    session.add_all(all_games)
    session.add_all(matches)


exit()

# Because of how sessions work behind the scenes - and the fact that we don't
# actually commit things to the database until a session is closed - I suspect
# that splitting them all off into individual sessions is probably required
# because I'm not quite sure how to synchronize these player objects; all of
# them will try and conflict with each other whenever a call to `get_player`
# is made. True, it returns the same underlying object, but from SQLAlchemy's
# (and Python's) perspective, these are two different things containing the
# exact same data.
#
# So if they use the same ORM object under the hood, that's ok; but since
# each of these functions gets the same data differently, the net result is
# that we can't do that on the Python side and expect everything to work.
# I believe the "correct" way to do this would be to share the player object
# between everything, but that violates the principle that each API call does
# its own thing. So we'll just have to put up with this.
#
# The alternative is to use `session.merge`, which reconciles this issue.
# Or, as has been implemented, to just use the actual field instead of relying
# on the ORM for the foreign key fields.
with db_con.session_maker.begin() as session:
    session.add_all(recent_games)
    session.merge(player_snapshot)
    session.merge(tl_snapshot)

# with controller.session_maker.begin() as session:
#     session.add_all(recent_games)

record_games = db_con.isolate_new_records(record_games)
with db_con.session_maker.begin() as session:
    # Auto-commits
    # session.add(player_snapshot)
    # session.add(tl_snapshot)
    # session.add_all(recent_games)
    session.add_all(record_games)
    # session.add_all(matches)


# import json
# with open('tetrio-dump.json') as fp:
#     data = json.load(fp)

# print(tetrio_api.get_global_data(data))
