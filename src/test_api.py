"""
Various testing routines to make sure the API works
"""
import controller, models, tetrio_api

# Test that everything works
controller.init_engine('sqlite+pysqlite:///:memory:')
models.create_tables(controller.engine)
a, b = tetrio_api.get_player_snapshots('kisun')

print(a.player)