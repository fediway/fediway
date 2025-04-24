
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger
import pandas as pd
import time

from app.modules.debezium import DebeziumEventHandler

class FeaturesEventHandler(DebeziumEventHandler):
    def __init__(self, fs: FeatureStore, source: str):
        self.fs = fs
        self.source = source

    async def created(self, data: dict):
        self._push(data)

    async def updated(self, old: dict, new: dict):
        self._push(new)

    async def deleted(self, data: dict):
        pass

    def _push(self, data):
        now = int(time.time())

        features = {}
        for key, value in data.items():
            if key not in ['author_id', 'account_id', 'event_time']:
                key = f"{key}"
            features[key] = value
        
        features['event_time'] = min(now, data['event_time'] * 1000)

        self.fs.push(
            self.source.replace('_features', '_stream'), 
            pd.DataFrame([features]), 
            to=PushMode.ONLINE
        )

        logger.debug(f"Pushed features to {self.source}.")