
from neo4j import Driver
from loguru import logger

from modules.herde import Herde
from modules.mastodon.models import StatusTag
from modules.debezium import DebeziumEventHandler

class StatusTagEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> StatusTag:
        return StatusTag(**data)

    async def created(self, status_tag: StatusTag):
        self.herde.add_status_tag(status_tag)
        logger.debug(f"Added status tag from {status_tag.status_id} to {status_tag.tag_id} memgraph.")

    async def updated(self, old: StatusTag, new: StatusTag):
        pass

    async def deleted(self, status_tag: StatusTag):
        self.herde.remove_status_tag(status_tag)
        logger.debug(f"Removed status tag from {status_tag.status_id} to {status_tag.tag_id} from memgraph.")