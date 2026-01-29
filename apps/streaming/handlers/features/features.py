import time

import pandas as pd
from feast import FeatureStore
from feast.data_source import PushMode

from modules.debezium import DebeziumEventHandler
from shared.utils.logging import log_debug


class FeaturesJsonEventHandler:
    def __init__(self, feature_store: FeatureStore, feature_view: str):
        self.feature_store = feature_store
        self.feature_view = feature_store.get_feature_view(feature_view)

    async def __call__(self, features: dict):
        features["event_time"] = min(int(time.time()), features["event_time"] * 1000)

        try:
            self.feature_store.push(
                self.feature_view.name + "_stream",
                pd.DataFrame([features]),
                to=PushMode.ONLINE,
            )
        except Exception as e:
            print(features)
            raise e

        log_debug(
            "Pushed features to online store",
            module="streaming",
            feature_view=self.feature_view.name,
            entities={e: features.get(e) for e in self.feature_view.entities},
        )


class FeaturesDebeziumEventHandler(DebeziumEventHandler, FeaturesJsonEventHandler):
    async def created(self, data: dict):
        await self(data)

    async def updated(self, old: dict, new: dict):
        await self(new)

    async def deleted(self, data: dict):
        pass  # TODO: delete from feature store
