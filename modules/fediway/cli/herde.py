
from neo4j import GraphDatabase, AsyncGraphDatabase
from datetime import datetime, timedelta
import typer
import time

from config import config
from modules.fediway.sources.herde import Herde
from app.core.db import get_db_session

app = typer.Typer(help="Herde commands.")

def get_driver():
    return GraphDatabase.driver(
        config.fediway.graph_url, 
        auth=config.fediway.graph_auth
    )

def get_async_driver():
    return AsyncGraphDatabase.driver(
        config.fediway.graph_url, 
        auth=config.fediway.graph_auth
    )

@app.command("verify-connection")
def verify_connection():
    with get_driver() as client:
        client.verify_connectivity()
        typer.echo("✅ Connection verified!")

@app.command("migrate")
def migrate():
    from modules.graph.memgraph import MemgraphMigrator

    migrator = MemgraphMigrator(
        driver=get_driver(), 
        migrations_path=config.fediway.herde_migrations_path
    )
            
    migrator.migrate()

@app.command("query")
def query(language: str = 'en'):
    with get_driver().session() as session:
        herde = Herde(session)

        print("start")
        for record in herde.get_relevant_statuses(language=language):
            print(record)

@app.command("seed")
def seed():
    from sqlmodel import select, exists, func, union_all
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_, and_
    from app.modules.models import Account, Status, Follow, Favourite
    from app.services.seed_herde_service import SeedHerdeService
    from tqdm import tqdm
    db = next(get_db_session())
    SeedHerdeService(db, get_driver()).seed()
    db.close()