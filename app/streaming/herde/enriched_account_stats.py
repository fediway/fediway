
from neo4j import Driver
from loguru import logger

from app.modules.models import Account
from modules.fediway.sources.herde import Herde

from app.modules.debezium import DebeziumEventHandler

class EnrichedAccountStatsEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    async def created(self, account: dict):
        self.herde.add_account_stats(account)
        logger.debug(f"Updated account stats {account['account_id']} in memgraph.")

    async def updated(self, old: dict, new: dict):
        self.herde.add_account_stats(new)
        logger.debug(f"Updared account stats {new['account_id']} in memgraph.")

    async def deleted(self, account: dict):
        pass