from pathlib import Path
import logging
import os
import sys

import dash
from dash import html
import dash_bootstrap_components as dbc

import db_con
import tetrio_api
import models

from dotenv import load_dotenv

logging.basicConfig(
    handlers=[
        logging.FileHandler("app.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def generate_container() -> html.Div:
    """
    Generate the main layout of the (effective) multipage app.
    """
    # "Home" page largely defined through a mix of the following two:
    # - https://dash-bootstrap-components.opensource.faculty.ai/examples/simple-sidebar/
    # - https://dash.plotly.com/urls

    SIDEBAR_STYLE = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    }

    CONTENT_STYLE = {
        "margin-left": "18rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }

    # Separte div by groups
    groups: dict[str, list] = {}
    for page in dash.page_registry.values():
        group = page["group"]
        if group not in groups:
            groups[group] = []

        groups[group].append(
            dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
        )

    # Generate group divs
    nav_eles = []
    for group_name, group_set in groups.items():
        nav_eles.append(
            html.Div(
                [html.B(group_name), dbc.Nav(group_set, vertical=True, pills=True)]
            )
        )

    # Intersperse individual group divs with horizontal rules
    # https://stackoverflow.com/questions/5920643/add-an-item-between-each-item-already-in-the-list
    nv = [html.Hr()] * (len(nav_eles) * 2 - 1)
    nv[0::2] = nav_eles

    sidebar = html.Div(
        [html.P("TETR.IO Statistics", className="display-6"), html.Hr(), html.Div(nv)],
        style=SIDEBAR_STYLE,
    )

    # page_container is dynamically defined depending on the current page of the
    # multi-page app.
    content = html.Div(dash.page_container, style=CONTENT_STYLE)

    return html.Div([sidebar, content])


if __name__ == "__main__":
    load_dotenv()
    
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USERNAME")
    db_pw = os.getenv("POSTGRES_PASSWORD")
    
    # This has to be done before the pages are registered
    logger.info(
        "Starting connection to DB and making tables if they don't already exist"
    )
    # Note that echo=True also echos logging.INFO level messages to the log.
    db_con.init_engine(
        f"postgresql+psycopg2://{db_user}:{db_pw}@localhost/{db_name}", echo=False
    )
    models.create_tables(db_con.engine)

    # Regenerate global data if needed
    snapshots = tetrio_api.regenerate_global_data(Path("./global_data").resolve())
    logger.info(
        f"Got {len(snapshots)} records back from regeneration - this may take a while if the app is being run for the first time"
    )
    with db_con.session_maker.begin() as session:
        session.add_all(snapshots)

    app = dash.Dash(
        __name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True
    )
    app.layout = generate_container()
    app.run_server(debug=True)
