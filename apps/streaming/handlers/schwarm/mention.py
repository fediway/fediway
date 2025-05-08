
from neo4j import Driver
from loguru import logger

from modules.mastodon.models import Mention
from modules.schwarm import Schwarm
from modules.debezium import DebeziumEventHandler

class MentionEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    def parse(data: dict) -> Mention:
        return Mention(**data)

    async def created(self, mention: Mention):
        if mention.silent:
            return

        self.schwarm.add_mention(mention)
        logger.debug(f"Added mention of {mention.account_id} by {mention.status_id} to memgraph.")

    async def updated(self, old: Mention, new: Mention):
        if mention.silent:
            return

    async def deleted(self, mention: Mention):
        if mention.silent:
            return

        self.schwarm.remove_mention(mention)
        logger.debug(f"Removed mention of {mention.account_id} by {mention.status_id} from memgraph.")