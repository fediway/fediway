
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

    def _cache_key(self, entities: list[dict[str, int]]) -> str:
        return ",".join(list(entities[0].keys()))

    def _get_cached(self, entities: list[dict[str, int]], features: list[str]):
        cache_key = self._cache_key(entities)

        if not cache_key in self.cache:
            return None, entities

        missing_entities = []
        entity_ids = pd.DataFrame(entities).values[:, 0]
        cached = []

        for feature in features:
            if not feature in self.cache[cache_key]:
                return None, entities
            feat = self.cache[cache_key][feature].reindex(entity_ids).dropna()
            cached.append(feat[~feat.index.duplicated(keep='last')])

        cached = pd.concat(cached, axis=1, join='inner')
        cached_entities = set(cached.index)

        return cached, [{cache_key: entity} for entity in entity_ids if not entity in cached_entities]

    def _remember(self, entities, df, features):
        cache_key = self._cache_key(entities)

        if "," in cache_key:
            return
        
        entity_ids = pd.DataFrame(entities).values[:, 0]

        if not cache_key in self.cache:
            self.cache[cache_key] = {}

        for column, feature_name in zip(df.columns, features):
            feat = df[column]
            feat.index = entity_ids
            if not feature_name in self.cache[cache_key]:
                self.cache[cache_key][feature_name] = feat
            else:
                feat = feat[~feat.index.isin(self.cache[cache_key][feature_name].index)]
                self.cache[cache_key][feature_name] = pd.concat([self.cache[cache_key][feature_name], feat])

    def get(self, entities: list[dict[str, int]], features: list[str]) -> np.ndarray | None:
        if len(features) == 0:
            return []

        if len(entities) == 0:
            return []

        start = time.time()

        cached_df, missing_entities = self._get_cached(entities, features)

        if len(missing_entities) == 0 and cached_df is not None:
            logger.info(f"Fetched cached features for {len(entities)} entities in {int((time.time() - start) * 1000)} milliseconds.")
            return cached_df.reindex(pd.DataFrame(entities).values[:, 0]).values

        df = self.fs.get_online_features(
            features=features,
            entity_rows=missing_entities
        ).to_df()

        self._remember(missing_entities, df, features)

        if cached_df is not None:
            df.index = pd.DataFrame(missing_entities).values[:, 0]
            df = pd.concat([df, cached_df]).reindex(pd.DataFrame(entities).values[:, 0])
            print(len(df), len(entities))

        logger.info(f"Fetched features for {len(entities)} entities in {int((time.time() - start) * 1000)} milliseconds.")

        return df.values