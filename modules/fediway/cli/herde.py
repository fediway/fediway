
from neo4j import GraphDatabase, AsyncGraphDatabase
from datetime import datetime, timedelta
from loguru import logger
import typer
import time

from config import config
from modules.fediway.sources.herde import Herde

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
    Herde(get_driver()).setup()

    typer.echo("✅ Migration completed!")

@app.command("purge")
def purge():
    with get_driver().session() as session:
        session.run("""
        MATCH (n)
        DETACH DELETE n;
        """)

    typer.echo("✅ Purged memgraph!")

@app.command("query")
def query(language: str = 'en'):
    herde = Herde(get_driver())

    print("start")
    for record in herde.get_relevant_statuses(language=language):
        print(record)

@app.command("rank")
def query():
    herde = Herde(get_driver())

    logger.info("Start computing account ranks...")
    with utils.duration("Computed account ranks in {:.3f} seconds"):
        herde.compute_account_rank()

    logger.info("Start computing tag ranks...")
    with utils.duration("Computed tag ranks in {:.3f} seconds"):
        herde.compute_tag_rank()

@app.command("clean")
def query():
    herde = Herde(get_driver())

    logger.info("Purging old statuses...")
    with utils.duration("Purged old statuses in {:.3f} seconds"):
        herde.purge_old_statuses(config.fediway.herde_max_status_age)

@app.command("seed")
def seed():
    from sqlmodel import select, exists, func, union_all
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_, and_
    from app.modules.models import Account, Status, Follow, Favourite
    from app.services.seed_herde_service import SeedHerdeService
    from tqdm import tqdm
    from app.core.db import get_db_session

    db = next(get_db_session())
    SeedHerdeService(db, get_driver()).seed()
    db.close()

    typer.echo("✅ Seeding completed!")
