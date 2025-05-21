import time

import pandas as pd
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger


class FeaturesEventHandler():
    def __init__(self, feature_store: FeatureStore, feature_view: str):
        self.feature_store = feature_store
        self.feature_view = feature_view
        self._non_feature_keys = set([
            'window_end', 'window_start', 'event_time'
        ])

    async def __call__(self, data: dict):
        now = int(time.time())

        features = {k: v for k, v in data.items() if k not in self._non_feature_keys}
        features["event_time"] = min(now, data["event_time"] * 1000)

        self.feature_store.push(
            self.feature_view + '_stream',
            pd.DataFrame([features]),
            to=PushMode.ONLINE,
        )

        logger.debug(f"Pushed {self.feature_view} features to online store.")
