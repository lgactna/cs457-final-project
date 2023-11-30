Simple TETR.IO statistics collector and viewer.

Python 3.11+ is required (earlier versions up to Python 3.9 might work).

To run, simply install the requirements:
```
pip install -r requirements.txt
```

And run the application:
```
python src/app.py
```

After this, you can simply navigate to `http://127.0.0.1:8050/` (or the link printed in stdout) to interact with the application.

Note that this program assumes that it is connecting to:
- a database called `postgres`
- running on `localhost` on the default port (5432)
- using a user called `postgres`
- with the password `password`

If these assumptions are *not* true, you will need to edit the relevant values in `.env` or change the `init_engine()` call in `src/app.py` as shown:
```python
db_con.init_engine(
    f"postgresql+psycopg2://{db_user}:{db_pw}@localhost/{db_name}", echo=False
)
```

When the app is run for the first time, it will attempt to pull data and generate the tables from `/global_data`. This may take several minutes. If you do not want this to happen, you can simply delete the JSON files in `/global_data`.

Note that SQLAlchemy (the ORM used for this project) will handle the creation of databases for you; the table schema *does not* need to exist ahead of time.