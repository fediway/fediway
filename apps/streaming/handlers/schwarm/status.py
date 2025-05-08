
from neo4j import Driver
from loguru import logger
from datetime import datetime, timedelta

from modules.mastodon.models import Status
from modules.schwarm import Schwarm
from modules.debezium import DebeziumEventHandler

from config import config

class StatusEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    def parse(data: dict) -> Status:
        return Status(**data)

    async def created(self, status: Status):
        limit = int((datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)).timestamp() * 1000)
        
        if status.created_at > limit:
            return
            
        if status.reblog_of_id is None:
            self.schwarm.add_status(status)
            logger.debug(f"Added status with id {status.id} to memgraph.")
        else:
            self.schwarm.add_reblog(status)
            logger.debug(f"Added reblog of {status.reblog_of_id} by {status.account_id} to memgraph.")

    async def updated(self, old: Status, new: Status):
        if new.deleted_at is not None:
            return await self.deleted(new)

    async def deleted(self, status: Status):
        if status.reblog_of_id is None:
            self.schwarm.remove_status(status)
            logger.debug(f"Removed status with id {status.id} from memgraph.")
        else:
            self.schwarm.remove_reblog(status)
            logger.debug(f"Removed reblog of {status.reblog_of_id} by {status.account_id} from memgraph.")