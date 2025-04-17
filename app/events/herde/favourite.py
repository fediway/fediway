
from neo4j import Driver
from loguru import logger

from app.modules.models import Favourite
from modules.fediway.sources.herde import Herde

class FavouriteEventHandler():
    def __init__(self, herde: Herde):
        self.herde = herde

    def parse(data: dict) -> Favourite:
        return Favourite(**data)

    async def created(self, favourite: Favourite):
        self.herde.add_favourite(favourite)
        logger.debug(f"Added favourite by {favourite.account_id} to {favourite.status_id} to memgraph.")

    async def updated(self, old: Favourite, new: Favourite):
        pass

    async def deleted(self, favourite: Favourite):
        self.herde.remove_favourite(favourite)
        logger.debug(f"Removed favourite by {favourite.account_id} to {favourite.status_id} from memgraph.")