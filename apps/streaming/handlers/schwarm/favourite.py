from loguru import logger

from modules.mastodon.models import Favourite
from modules.schwarm import Schwarm

from modules.debezium import DebeziumEventHandler


class FavouriteEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    def parse(data: dict) -> Favourite:
        return Favourite(**data)

    async def created(self, favourite: Favourite):
        self.schwarm.add_favourite(favourite)
        logger.debug(
            f"Added favourite by {favourite.account_id} to {favourite.status_id} to memgraph."
        )

    async def updated(self, old: Favourite, new: Favourite):
        pass

    async def deleted(self, favourite: Favourite):
        self.schwarm.remove_favourite(favourite)
        logger.debug(
            f"Removed favourite by {favourite.account_id} to {favourite.status_id} from memgraph."
        )
