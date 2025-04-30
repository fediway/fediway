
from neo4j import Driver
from loguru import logger

from app.modules.models import Follow
from modules.fediway.sources.herde import Herde

from app.modules.debezium import DebeziumEventHandler

class FollowEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> Follow:
        return Follow(**data)

    async def created(self, follow: Follow):
        self.herde.add_follow(follow)
        logger.debug(f"Added follow from {follow.account_id} to {follow.target_account_id} to memgraph.")

    async def updated(self, old: Follow, new: Follow):
        pass

    async def deleted(self, follow: Follow):
        self.herde.remove_follow(follow)
        logger.debug(f"Removed follow from {follow.account_id} to {follow.target_account_id} from memgraph.")