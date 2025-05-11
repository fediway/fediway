
from feast import FeatureStore
import pandas as pd
import numpy as np
from loguru import logger
import time

from shared.core.feast import feature_store
from modules.mastodon.models import Status, StatusStats
from modules.fediway.feed.features import Features

class FeatureService(Features):
    cache = {}

    def __init__(self, fs: FeatureStore = feature_store):
        self.fs = fs

    def get(self, entities: list[dict[str, int]], features: list[str]) -> np.ndarray | None:
        if len(features) == 0:
            return []

        if len(entities) == 0:
            return []

        start = time.time()

        data = self.fs.get_online_features(
            features=features,
            entity_rows=entities
        ).to_df().values

        logger.info(f"Fetched features for {len(entities)} entities in {int((time.time() - start) * 1000)} milliseconds.")

        return data