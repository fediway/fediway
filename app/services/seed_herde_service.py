
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
from app.modules.models import Account, Status, StatusStats, Follow, Favourite
from modules.fediway.sources.herde import Herde
import app.utils as utils

def query_line(query):
    return query.strip().replace('  ', '').replace('\n', ' ') + "\n"

class SeedHerdeService:
    def __init__(self, db: DBSession, driver: Driver, chunk_size: int = 10_000):
        self.db = db
        self.driver = driver
        self.herde = Herde(self.driver)
        self.chunk_size = chunk_size
        self.max_age = datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)
        self.path = Path(f'{config.app.data_path}/herde')

    def seed(self):
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(exist_ok=True, parents=True)

        with utils.duration("Set up memgraph in {:.4f} seconds"):
            self.herde.setup()

        with utils.duration("Created account seeds in {:.4f} seconds"):
            self.create_account_seeds()

        with utils.duration("Created status seeds in {:.4f} seconds"):
            self.create_status_seeds()

        with utils.duration("Created follow seeds in {:.4f} seconds"):
            self.create_follow_seeds()

        with utils.duration("Created favourite seeds in {:.4f} seconds"):
            self.create_favourite_seeds()

        logger.info("Start seeding accounts...")
        with utils.duration("Seeded accounts in {:.4f} seconds"):
            self.seed_files(self.path / 'accounts')

        logger.info("Start seeding statuses...")
        with utils.duration("Seeded statuses in {:.4f} seconds"):
            self.seed_files(self.path / 'statuses')

        logger.info("Start seeding follows...")
        with utils.duration("Seeded follows in {:.4f} seconds"):
            self.seed_files(self.path / 'follows')

        logger.info("Start seeding favourites...")
        with utils.duration("Seeded favourites in {:.4f} seconds"):
            self.seed_files(self.path / 'favourites')

        # clear files
        shutil.rmtree(self.path)

        logger.info("Start computing account ranks...")
        with utils.duration("Computed account ranks in {:.4f} seconds"):
            self.herde.compute_account_rank()

    def seed_files(self, path):
        files = sorted(path.glob("*.cypher"))
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

    def create_status_seeds(self, batch_size: int = 100):
        path = self.path / 'statuses'
        path.mkdir(exist_ok=True, parents=True)

        query = (
            select(
                Status.id, 
                Status.account_id, 
                Status.language, 
                Status.created_at, 
                StatusStats.favourites_count,
                StatusStats.replies_count,
                StatusStats.reblogs_count,
            )
            .join(StatusStats, StatusStats.status_id == Status.id, isouter=False)
            .where(Status.created_at > self.max_age)
        )

        chunk = 0
        queries = []
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            for row in batch:
                row = dict(zip(row.keys(), row.values()))
                row['created_at'] = row['created_at'].timestamp()
                queries.append(query_line("""
                MATCH (a:Account {{id: {account_id}}})
                MERGE (s:Status {{id: {id}}})
                ON CREATE SET 
                    s.language = '{language}', 
                    s.created_at = {created_at},
                    s.num_favs = {favourites_count},
                    s.num_replies = {replies_count},
                    s.num_reblogs = {reblogs_count}
                CREATE (a)-[:CREATED_BY]->(s);
                """.format(**row)))

                if len(queries) > self.chunk_size:
                    with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                        f.writelines(queries)
                    chunk += 1
                    queries = []
        
        if len(queries) > 0:
            with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                f.writelines(queries)

    def create_account_seeds(self, batch_size: int = 100):
        path = self.path / 'accounts'
        path.mkdir(exist_ok=True, parents=True)

        StatusAlias = aliased(Status)
        StatusAlias2 = aliased(Status)

        query = (
            select(
                Account.id, 
                exists(Status.id).where(
                    Status.account_id == Account.id,
                    Status.created_at > self.max_age,
                ).label("has_status"),
                exists(Favourite.id)
                .where(Favourite.account_id == Account.id)
                .where(
                    exists(StatusAlias.id)
                    .where(
                        StatusAlias.id == Favourite.status_id,
                        StatusAlias.created_at > self.max_age,
                    )
                ).label("has_favourite"),
                exists(Follow.id)
                .where(or_(
                    Follow.account_id == Account.id,
                    Follow.account_id == Account.id,
                ))
                .label("has_follow"),
                func.avg(StatusStats.favourites_count).label('avg_favs'),
                func.avg(StatusStats.reblogs_count).label('avg_reblogs'),
                func.avg(StatusStats.replies_count).label('avg_replies'),
            )
            .outerjoin(StatusAlias2, StatusAlias2.account_id == Account.id)
            .outerjoin(StatusStats, StatusStats.status_id == StatusAlias2.id)
            .group_by(Account.id)
        )

        chunk = 0
        queries = []
        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            account_ids = []
            for row in batch:
                if not (row['has_status'] or row['has_favourite'] or row['has_follow']):
                    continue
                queries.append(query_line("""
                MERGE (a:Account {{id: {id}}})
                ON CREATE SET
                    a.avg_favs = {avg_favs},
                    a.avg_replies = {avg_replies},
                    a.avg_reblogs = {avg_reblogs};
                """.format(
                    id=row['id'],
                    avg_favs=float(row['avg_favs'] or 0.0),
                    avg_reblogs=float(row['avg_reblogs'] or 0.0),
                    avg_replies=float(row['avg_replies'] or 0.0),
                )))
            
                if len(queries) > self.chunk_size:
                    with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                        f.writelines(queries)
                    chunk += 1
                    queries = []
        
        if len(queries) > 0:
            with open(path / f'chunk_{chunk}.cypher', 'w') as f:
                f.writelines(queries)