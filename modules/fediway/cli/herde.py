
from neo4j import GraphDatabase, AsyncGraphDatabase
import typer

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
    from sqlmodel import select, exists, func
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_
    from app.modules.models import Account, Status, Follow, Favourite
    from tqdm import tqdm
    db = next(get_db_session())
    with get_driver().session() as session:
        herde = Herde(session)

        herde.setup()

        # accounts = db.exec(
        #     select(Account)
        #     .options(
        #         selectinload(Account.statuses)
        #         .options(selectinload(Status.stats))
        #     )
        #     .where(or_(
        #         exists(Status.id).where(Status.account_id == Account.id),
        #         exists(Favourite.id).where(Favourite.account_id == Account.id),
        #     ))
        #     .execution_options(yield_per=100)
        # ).all()
        # total = db.scalar((
        #     select(func.count(Account.id))
        #     .where(or_(
        #         exists(Status.id).where(Status.account_id == Account.id),
        #         exists(Favourite.id).where(Favourite.account_id == Account.id),
        #     ))
        # ))

        # bar = tqdm(
        #     desc="Accounts",
        #     total=total
        # )

        # for account in accounts:
        #     herde.add_account(account)
        #     for status in account.statuses:
        #         if status.stats is None:
        #             continue
        #         herde.add_status(status)
        #     bar.update(1)

        # bar.close()

        # follows = db.exec(select(Follow).execution_options(yield_per=100)).all()
        # total = db.scalar(select(func.count(Follow.id)))

        # bar = tqdm(
        #     desc="Follows",
        #     total=total
        # )

        # for follow in follows:
        #     herde.add_follow(follow.account_id, follow.target_account_id)
        #     bar.update(1)
        
        # bar.close()

        # favourites = db.exec(select(Favourite).execution_options(yield_per=100)).all()
        # total = db.scalar(select(func.count(Favourite.id)))

        # bar = tqdm(
        #     desc="Favourites",
        #     total=total
        # )

        # for favourite in favourites:
        #     herde.add_favourite(favourite.account_id, favourite.status_id)
        #     bar.update(1)
        
        # bar.close()

        herde.compute_diversity_scores()