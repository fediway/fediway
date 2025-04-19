
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger
import time

from ..base import DebeziumEventHandler

class AccountAuthorFeaturesEventHandler(DebeziumEventHandler):

    def __init__(self, fs: FeatureStore):
        self.fs = fs

    async def created(self, data: dict):
        self._push(data)
        logger.debug(f"Created account_author_features.")

    async def updated(self, old: dict, new: dict):
        self._push(new)
        logger.debug(f"Updated account_author_features.")

    async def deleted(self, data: dict):
        pass

    def _push(self, data):
        now = int(time.time() * 1000)

        self.fs.push("account_author_features", [{
            'account_id': data['account_id'],
            'author_id': data['author_id'],
            'event_time': min(now, data['window_end']),

            'fav_count_7d': data['fav_count_7d'],
            'reblogs_count_7d': data['reblogs_count_7d'],
            'replies_count_7d': data['replies_count_7d'],

            'fav_count_30d': data['fav_count_30d'],
            'reblogs_count_30d': data['reblogs_count_30d'],
            'replies_count_30d': data['replies_count_30d'],
        }], to=PushMode.ONLINE_AND_OFFLINE)