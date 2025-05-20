from neo4j import Driver
from loguru import logger

from modules.mastodon.models import Account
from modules.schwarm import Schwarm

from modules.debezium import DebeziumEventHandler


class AccountEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    def parse(data: dict) -> Account:
        return Account(**data)

    async def created(self, account: Account):
        if account.silenced_at is not None:
            return await self.deleted(account)
        elif account.suspended_at is not None:
            return await self.deleted(account)
        elif account.silenced_at is not None:
            return await self.deleted(account)

        self.schwarm.add_account(account)
        logger.debug(f"Added account {account.acct} to memgraph.")

    async def updated(self, old: Account, new: Account):
        if new.silenced_at is not None:
            return await self.deleted(account)
        elif new.suspended_at is not None:
            return await self.deleted(account)
        elif new.silenced_at is not None:
            return await self.deleted(account)
        elif new.indexable is not None and not new.indexable:
            return await self.deleted(account)

        if old.indexable != new.indexable:
            self.schwarm.add_account(account)
            logger.debug(f"Updared account {account.acct} in memgraph.")

    async def deleted(self, account: Account):
        self.schwarm.remove_account(account)
        logger.debug(f"Removed account {account.acct} from memgraph.")
