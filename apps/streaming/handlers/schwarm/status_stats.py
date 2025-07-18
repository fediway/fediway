from datetime import datetime, timedelta
from loguru import logger

from modules.debezium import DebeziumEventHandler
from modules.mastodon.models import StatusStats
from modules.schwarm import Schwarm

from config import config


def _limit():
    return int(
        (
            datetime.now() - timedelta(days=config.fediway.feed_max_age_in_days)
        ).timestamp()
        * 1000
    )


class StatusStatsEventHandler(DebeziumEventHandler):
    def __init__(self, schwarm: Schwarm):
        self.schwarm = schwarm

    def parse(data: dict) -> StatusStats:
        return StatusStats(**data)

    async def created(self, status_stats: StatusStats):
        if status_stats.created_at < _limit():
            return

        self.schwarm.add_status_stats(status_stats)
        logger.debug(f"Added status stats for {status_stats.status_id} to memgraph.")

    async def updated(self, old: StatusStats, new: StatusStats):
        if new.created_at < _limit():
            return

        self.schwarm.add_status_stats(new)
        logger.debug(f"Added status stats for {new.status_id} to memgraph.")

    async def deleted(self, status_stats: StatusStats):
        pass
