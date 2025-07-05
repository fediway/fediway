import time

import pandas as pd
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger

from modules.debezium import DebeziumEventHandler


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

        entities_desc = ",".join(
            [f"{e}:{features.get(e)}" for e in self.feature_view.entities]
        )

        logger.debug(
            f"Pushed {self.feature_view.name}[{entities_desc}] features to online store."
        )


class FeaturesDebeziumEventHandler(DebeziumEventHandler, FeaturesJsonEventHandler):
    async def created(self, data: dict):
        await self(data)

    async def updated(self, old: dict, new: dict):
        await self(new)

    async def deleted(self, data: dict):
        pass  # TODO: delete from feature store
