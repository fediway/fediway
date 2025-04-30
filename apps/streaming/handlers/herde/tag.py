
from neo4j import Driver
from loguru import logger

from modules.herde import Herde
from modules.mastodon.models import Tag
from modules.debezium import DebeziumEventHandler

class TagEventHandler(DebeziumEventHandler):
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> Tag:
        return Tag(**data)

    async def created(self, tag: Tag):
        self.herde.add_tag(tag)
        logger.debug(f"Added tag {tag.name} to memgraph.")

    async def updated(self, old: Tag, new: Tag):
        pass

    async def deleted(self, tag: Tag):
        self.herde.remove_tag(tag)
        logger.debug(f"Removed tag {tag.name} from memgraph.")