
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger
import time

from ..base import DebeziumEventHandler

class FeaturesEventHandler(DebeziumEventHandler):

    def __init__(self, fs: FeatureStore, fv: str, source: str):
        self.fs = fs
        self.source = source
        self.fv = fv

    async def created(self, data: dict):
        self._push(data)
        

    async def updated(self, old: dict, new: dict):
        self._push(new)

    async def deleted(self, data: dict):
        pass

    def _push(self, data):
        now = int(time.time() * 1000)

        features = {}
        for key, value in data.items():
            if key not in ['author_id', 'account_id', 'event_time']:
                key = f"{self.source.replace('_features', '')}_{key}"
            features[key] = value
        print(features.keys())
        features['event_time'] = min(now, data['event_time'])

        logger.debug(f"Pushing features to {self.source}.")

        self.fs.push(self.fv, [data])

        logger.debug(f"Pushed features to {self.source}.")