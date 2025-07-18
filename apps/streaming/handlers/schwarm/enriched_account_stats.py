from loguru import logger

from modules.debezium import DebeziumEventHandler
from modules.schwarm import Schwarm


class EnrichedAccountStatsEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    async def created(self, account: dict):
        self.schwarm.add_account_stats(account)
        logger.debug(f"Updated account stats {account['account_id']} in memgraph.")

    async def updated(self, old: dict, new: dict):
        self.schwarm.add_account_stats(new)
        logger.debug(f"Updared account stats {new['account_id']} in memgraph.")

    async def deleted(self, account: dict):
        pass
