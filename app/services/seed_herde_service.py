
from sqlmodel import Session as DBSession, select, func, text
from sqlalchemy.orm import selectinload
from neo4j import Session as GraphSession
from datetime import datetime, timedelta
from tqdm import tqdm

from config import config
from app.modules.models import Account, Status, Follow, Favourite
from modules.fediway.sources.herde import Herde
import app.utils as utils

class SeedHerdeService:
    def __init__(self, db: DBSession, graph: GraphSession):
        self.db = db
        self.graph = graph
        self.herde = Herde(self.graph)
        self.max_age = datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)

    def seed(self):
        # memgraph setup
        with utils.duration("Set up memgraph in {:.4f} seconds"):
            self.herde.setup()

        self.seed_account_and_statuses()

    def seed_account_and_statuses(self, batch_size: int = 100):
        total = self.db.scalar(select(func.count(Account.id)))
        bar = tqdm(desc="Accounts", total=total)

        query = select(Account.id, Account.domain)

        for batch in utils.iter_db_batches(self.db, query, batch_size = batch_size):
            account_ids = [row['id'] for row in batch]

            # load statuses
            statuses = self.db.exec(
                select(Status)
                .where(Status.account_id.in_(account_ids))
                # .where(Status.created_at < self.max_age)
                .options(selectinload(Status.stats))
            ).all()
            statuses_map = {account_id: [] for account_id in account_ids}
            for s in statuses:
                statuses_map[s.account_id].append(s)

            accounts = []
            for row in batch:
                account = Account(**row)
                account.statuses = statuses_map.get(account.id, [])
                self.herde.add_account(account)
            self.herde.add_statuses([s for s in statuses if s.stats is not None])

            bar.update(len(batch))