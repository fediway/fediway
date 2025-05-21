from datetime import timedelta

import typer
from loguru import logger

import modules.utils as utils
from config import config

app = typer.Typer(help="Schwarm commands.")


def get_driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        config.fediway.memgraph_url, auth=config.fediway.memgraph_auth
    )


def get_async_driver():
    from neo4j import AsyncGraphDatabase

    return AsyncGraphDatabase.driver(
        config.fediway.memgraph_url, auth=config.fediway.memgraph_auth
    )


@app.command("verify-connection")
def verify_connection():
    with get_driver() as client:
        client.verify_connectivity()
        typer.echo("✅ Connection verified!")


@app.command("migrate")
def migrate():
    from modules.schwarm import Schwarm

    Schwarm(get_driver()).setup()

    typer.echo("✅ Migration completed!")


@app.command("purge")
def purge():
    with get_driver().session() as session:
        session.run("""
        MATCH (n)
        DETACH DELETE n;
        """)

    typer.echo("✅ Purged memgraph!")


@app.command("collect")
def collect(language: str = "en"):
    from modules.fediway.sources.schwarm import (
        TrendingStatusesByInfluentialUsers,
    )

    # source = MostInteractedByAccountsSource(
    #     driver=get_driver(),
    #     account_ids=[114397974544358424, 114397974544358424]
    #     # account_id=114394115240930061,
    #     # language='en',
    #     # max_age=timedelta(days=14)
    # )

    source = TrendingStatusesByInfluentialUsers(
        driver=get_driver(), language=language, max_age=timedelta(days=28)
    )

    # source = TrendingStatusesByTagsInCommunity(
    #     driver=get_driver(),
    #     account_id=114398075274349836
    # )

    with utils.duration("Collected in {:3f} seconds"):
        for status_id in source.collect(10):
            print(status_id)
    exit(())

    from modules.schwarm import Schwarm

    schwarm = Schwarm(get_driver())

    print("start")
    for record in schwarm.get_relevant_statuses(language=language):
        print(record)


@app.command("rank")
def rank():
    from modules.schwarm import Schwarm

    schwarm = Schwarm(get_driver())

    logger.info("Start computing account ranks...")
    with utils.duration("Computed account ranks in {:.3f} seconds"):
        schwarm.compute_account_rank()

    logger.info("Start computing tag ranks...")
    with utils.duration("Computed tag ranks in {:.3f} seconds"):
        schwarm.compute_tag_rank()


@app.command("clean")
def clean():
    from modules.schwarm import Schwarm

    schwarm = Schwarm(get_driver())

    logger.info("Purging old statuses...")
    with utils.duration("Purged old statuses in {:.3f} seconds"):
        schwarm.purge_old_statuses(config.fediway.schwarm_max_status_age)


@app.command("seed")
def seed():
    from shared.core.db import db_session
    from shared.services.seed_schwarm_service import SeedSchwarmService

    with db_session() as db:
        SeedSchwarmService(db, get_driver()).seed()

    typer.echo("✅ Seeding completed!")
