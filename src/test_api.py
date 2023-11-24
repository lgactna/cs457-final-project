"""
Various testing routines to make sure the API works
"""
import controller, models, tetrio_api

# Test that everything works
controller.init_engine('sqlite+pysqlite:///:memory:', echo=False)
models.create_tables(controller.engine)
player_snapshot, tl_snapshot = tetrio_api.get_player_snapshots('kisun')

print(player_snapshot)
print(tl_snapshot)
uuid = player_snapshot.player.id

print(tetrio_api.get_player_recent(uuid))
print(tetrio_api.get_player_records(uuid))
matches = tetrio_api.get_player_matches(uuid)
for match in matches:
    print(match.tl_players)

import json
with open('tetrio-dump.json') as fp:
    data = json.load(fp)
    
print(tetrio_api.get_global_data(data))