
from neo4j import Driver
from loguru import logger
from datetime import datetime, timedelta

from app.modules.models import Status
from modules.fediway.sources.herde import Herde

from config import config
from app.modules.debezium import DebeziumEventHandler

class StatusEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> Status:
        return Status(**data)

    async def created(self, status: Status):
        limit = int((datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)).timestamp() / 1000)
        
        if status.created_at > limit:
            return
            
        if status.reblog_of_id is None:
            self.herde.add_status(status)
            logger.debug(f"Added status with id {status.id} to memgraph.")
        else:
            self.herde.add_reblog(status)
            logger.debug(f"Added reblog of {status.reblog_of_id} by {status.account_id} to memgraph.")

    async def updated(self, old: Status, new: Status):
        if new.deleted_at is not None:
            return await self.deleted(new)

    async def deleted(self, status: Status):
        if status.reblog_of_id is None:
            self.herde.remove_status(status)
            logger.debug(f"Removed status with id {status.id} from memgraph.")
        else:
            self.herde.remove_reblog(status)
            logger.debug(f"Removed reblog of {status.reblog_of_id} by {status.account_id} from memgraph.")