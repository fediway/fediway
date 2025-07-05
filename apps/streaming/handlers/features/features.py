import time

import pandas as pd
from feast import FeatureStore
from feast.data_source import PushMode
from loguru import logger

from modules.debezium import DebeziumEventHandler


class FeaturesJsonEventHandler:
    def __init__(self, feature_store: FeatureStore, feature_view: str):
        self.feature_store = feature_store
        self.feature_view = feature_view
        self._non_feature_keys = set(["window_end", "window_start", "event_time"])

    async def __call__(self, data: dict):
        now = int(time.time())

        features = {k: v for k, v in data.items() if k not in self._non_feature_keys}
        features["event_time"] = min(now, data["event_time"] * 1000)

        entity_ids = [features.get(e) for e in self.feature_view.entities]

        try:
            self.feature_store.push(
                self.feature_view + "_stream",
                pd.DataFrame([features]),
                to=PushMode.ONLINE,
            )
        except Exception as e:
            print(features)
            raise e

        entities_desc = ",".join(
            [f"{e}:{eid}" for eid, e in zip(entity_ids, self.feature_view.entities)]
        )

        logger.debug(
            f"Pushed {self.feature_view}[{entities_desc}] features to online store."
        )


class FeaturesDebeziumEventHandler(DebeziumEventHandler, FeaturesJsonEventHandler):
    async def created(self, data: dict):
        logger.debug(f"Debezium features: create")
        self(data)

    async def updated(self, old: dict, new: dict):
        logger.debug(f"Debezium features: update")
        self(new)

    async def deleted(self, data: dict):
        logger.debug(f"Debezium features: delete")
        pass  # TODO: delete from feature store
