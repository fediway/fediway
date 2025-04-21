
from neo4j import Driver
from loguru import logger

from app.modules.models import Account
from modules.fediway.sources.herde import Herde

from app.modules.debezium import DebeziumEventHandler

class AccountEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> Account:
        return Account(**data)

    async def created(self, account: Account):
        self.herde.add_account(account)
        logger.debug(f"Added account {account.acct} to memgraph.")

    async def updated(self, old: Account, new: Account):
        if new.silenced_at is not None:
            await self.deleted(account)
        elif new.suspended_at is not None:
            await self.deleted(account)
        elif new.silenced_at is not None:
            await self.deleted(account)
        
        if old.indexable != new.indexable:
            self.add_account(account)
            logger.debug(f"Updared account {account.acct} in memgraph.")

    async def deleted(self, account: Account):
        self.herde.remove_account(account)
        logger.debug(f"Removed account {account.acct} from memgraph.")