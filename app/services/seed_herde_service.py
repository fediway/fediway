
from sqlmodel import Session as DBSession, select, func, exists
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy import or_, and_
from neo4j import Driver
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from tqdm import tqdm
import shutil

from config import config
from app.modules.models import Account, Status, StatusStats, Follow, Favourite, Tag, StatusTag, Mention
from modules.fediway.sources.herde import Herde
import app.utils as utils

def query_line(query):
    return query.strip().replace('  ', '').replace('\n', ' ') + "\n"

class SeedHerdeService:
    def __init__(self, db: DBSession, driver: Driver):
        self.db = db
        self.driver = driver
        self.herde = Herde(self.driver)
        self.max_age = datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)

    def seed(self):

        with utils.duration("Set up memgraph in {:.3f} seconds"):
            self.herde.setup()

        with utils.duration("Created favourite seeds in {:.3f} seconds"):
            self.seed_tags()

        with utils.duration("Seeded accounts in {:.3f} seconds"):
            self.seed_accounts()

        with utils.duration("Seeded statuses in {:.3f} seconds"):
            self.seed_statuses()

        with utils.duration("Seeded status stats in {:.3f} seconds"):
            self.seed_status_stats()

        with utils.duration("Seeded reblogs in {:.3f} seconds"):
            self.seed_reblogs()

        with utils.duration("Seeded follows in {:.3f} seconds"):
            self.seed_follows()

        with utils.duration("Created favourite seeds in {:.3f} seconds"):
            self.seed_favourites()

        with utils.duration("Created status tag seeds in {:.3f} seconds"):
            self.seed_statuses_tags()

        with utils.duration("Created mention seeds in {:.3f} seconds"):
            self.seed_mentions()

        logger.info("Start computing account ranks...")
        with utils.duration("Computed account ranks in {:.3f} seconds"):
            self.herde.compute_account_rank()

        logger.info("Start computing tag ranks...")
        with utils.duration("Computed tag ranks in {:.3f} seconds"):
            self.herde.compute_tag_rank()
        
    def seed_files(self, path):
        files = sorted(path.glob("*.cypher"))
        logger.info(f"{len(files)} chunks.")
        for file in files:
            with open(file) as f:
                queries = [q.strip() for q in f.read().split(';') if q.strip()]

                for query in tqdm(queries, desc=file.stem):
                    with self.driver.session() as graph:
                        graph.run(query)

    def create_favourite_seeds(self, batch_size: int = 100):
        path = self.path / 'favourites'
        path.mkdir(exist_ok=True, parents=True)

        query = (
            select(Favourite.account_id, Favourite.status_id)
            .join(Status, and_(
                Status.id == Favourite.status_id,
                Status.created_at > self.max_age
            ), isouter=False)
        )

        chunk = 0
        queries = []
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                row = dict(zip(row.keys(), row.values()))
                
                queries.append(query_line("""
                MATCH (a:Account {{id: {account_id}}})
                MATCH (s:Status {{id: {status_id}}})
                MERGE (a)-[:FAVOURITES]->(s);
                """.format(**row)))

                if len(queries) > self.chunk_size:
                    with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                        f.writelines(queries)
                    chunk += 1
                    queries = []
        
        if len(queries) > 0:
            with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                f.writelines(queries)

    def create_follow_seeds(self, batch_size: int = 100):
        path = self.path / 'follows'
        path.mkdir(exist_ok=True, parents=True)

        query = select(Follow.account_id, Follow.target_account_id)

        chunk = 0
        queries = []
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                row = dict(zip(row.keys(), row.values()))
                
                queries.append(query_line("""
                MATCH (a:Account {{id: {account_id}}})
                MATCH (b:Account {{id: {target_account_id}}})
                MERGE (a)-[:FOLLOWS]->(b);
                """.format(**row)))

                if len(queries) > self.chunk_size:
                    with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                        f.writelines(queries)
                    chunk += 1
                    queries = []
        
        if len(queries) > 0:
            with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                f.writelines(queries)

    def seed_statuses(self, batch_size: int = 100):
        query = (
            select(
                Status.id, 
                Status.account_id, 
                Status.language, 
                Status.created_at, 
            )
            .where(Status.created_at > self.max_age)
            .where(Status.reblog_of_id.is_(None))
        )
        total = self.db.scalar(
            select(func.count(Status.id))
            .where(Status.created_at > self.max_age)
            .where(Status.reblog_of_id.is_(None))
        )

        bar = tqdm(desc="Statuses", total=total, unit="statuses")
        
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_status(Status(**row))
                bar.update(1)

    def seed_reblogs(self, batch_size: int = 100):
        query = (
            select(
                Status.id, 
                Status.account_id, 
                Status.language, 
                Status.created_at, 
            )
            .where(Status.created_at > self.max_age)
            .where(~Status.reblog_of_id.is_(None))
        )
        total = self.db.scalar(
            select(func.count(Status.id))
            .where(Status.created_at > self.max_age)
            .where(~Status.reblog_of_id.is_(None))
        )

        bar = tqdm(desc="Statuses", total=total, unit="statuses")
        
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_reblog(Status(**row))
                bar.update(1)

    def seed_favourites(self, batch_size: int = 100):
        query = (
            select(Favourite)
            .join(Status, and_(
                Status.id == Favourite.status_id,
                Status.created_at > self.max_age
            ))
        )
        total = self.db.scalar(
            select(func.count(Favourite.id))
            .join(Status, and_(
                Status.id == Favourite.status_id,
                Status.created_at > self.max_age
            ))
        )

        bar = tqdm(desc="Favourites", total=total, unit="favourites")
        
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_favourite(row)
                bar.update(1)

    def seed_status_stats(self, batch_size: int = 100):
        query = (
            select(StatusStats)
            .join(Status, and_(
                Status.id == StatusStats.status_id,
                Status.created_at > self.max_age
            ))
        )
        total = self.db.scalar(
            select(func.count(StatusStats.status_id))
            .join(Status, and_(
                Status.id == StatusStats.status_id,
                Status.created_at > self.max_age
            ))
        )

        bar = tqdm(desc="Status Stats", total=total, unit="status_stats")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_status_stats(row)
                bar.update(1)

    def seed_follows(self, batch_size: int = 100):
        query = select(Follow)
        total = self.db.scalar(select(func.count(Follow.id)))

        bar = tqdm(desc="Follows", total=total, unit="follows")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_follow(Account(**row))
                bar.update(1)

    def seed_accounts(self, batch_size: int = 100):
        query = select(Account.id, Account.indexable)
        total = self.db.scalar(select(func.count(Account.id)))

        bar = tqdm(desc="Accounts", total=total, unit="accounts")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_account(Account(**row))
                bar.update(1)

    def seed_tags(self, batch_size: int = 100):
        query = select(Tag)
        total = self.db.scalar(select(func.count(Tag.id)))

        bar = tqdm(desc="Tags", total=total, unit="tags")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_tag(row)
                bar.update(1)

    def seed_statuses_tags(self, batch_size: int = 100):
        query = select(StatusTag)
        total = self.db.scalar(select(func.count(StatusTag.status_id)))

        bar = tqdm(desc="Status Tags", total=total, unit="statuses_tags")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_status_tag(row)
                bar.update(1)

    def seed_mentions(self, batch_size: int = 100):
        query = select(Mention)
        total = self.db.scalar(select(func.count(Mention.id)))

        bar = tqdm(desc="Mentions", total=total, unit="mentions")

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                self.herde.add_mention(row)
                bar.update(1)
