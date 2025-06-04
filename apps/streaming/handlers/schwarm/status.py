from datetime import datetime, timedelta
from loguru import logger

from config import config
from modules.debezium import DebeziumEventHandler
from modules.mastodon.models import Status
from modules.schwarm import Schwarm


class SchwarmStatusScoreEventHandler:
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    async def __call__(self, status: dict):
        limit = int(
            (
                datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)
            ).timestamp()
            * 1000
        )

        # if status.created_at < limit:
        #     return

        if status.reblog_of_id is None:
            self.schwarm.add_status(status)
            logger.debug(f"Added status with id {status.id} to memgraph.")
        else:
            self.schwarm.add_reblog(status)
            logger.debug(
                f"Added reblog of {status.reblog_of_id} by {status.account_id} to memgraph."
            )
