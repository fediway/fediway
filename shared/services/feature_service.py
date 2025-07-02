import numpy as np
import pandas as pd
from feast import FeatureStore
from loguru import logger
from fastapi import BackgroundTasks
from datetime import datetime
import time

from modules.fediway.feed.features import Features
from shared.core.feast import feature_store


class FeatureService(Features):
    def __init__(
        self,
        fs: FeatureStore = feature_store,
        background_tasks: BackgroundTasks | None = None,
        event_time: datetime = datetime.now(),
        offline_store: bool = False,
    ):
        self.cache = {}
        self.fs = fs
        self.background_tasks = background_tasks
        self.event_time = event_time
        self.offline_store = offline_store

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
            cached.append(feat[~feat.index.duplicated(keep="last")])

        cached = pd.concat(cached, axis=1, join="inner")
        cached_entities = set(cached.index)

        return cached, [
            {cache_key: entity}
            for entity in entity_ids
            if not entity in cached_entities
        ]

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
                self.cache[cache_key][feature_name] = feat[
                    ~feat.index.duplicated(keep="last")
                ]
            else:
                feat = pd.concat([self.cache[cache_key][feature_name], feat])
                self.cache[cache_key][feature_name] = feat[
                    ~feat.index.duplicated(keep="last")
                ]

    def ingest_to_offline_store(
        self, features: pd.DataFrame, event_time: datetime | None = None
    ):
        feature_views = set([c.split("__")[0] for c in features.columns if "__" in c])
        for fv_name in feature_views:
            feature_view = self.fs.get_feature_view(fv_name)
            if feature_view is None:
                continue
            columns = [
                c
                for c in features.columns
                if c.startswith(fv_name) or c in feature_view.entities
            ]
            feature_names = [c.split("__")[-1] for c in columns]
            df = features[columns].rename(columns=dict(zip(columns, feature_names)))
            df["event_time"] = int((event_time or self.event_time).timestamp())

            try:
                result = self.fs.write_to_offline_store(
                    fv_name,
                    df=df,
                )
            except Exception as e:
                logger.error(e)

    async def get(
        self,
        entities: list[dict[str, int]],
        features: list[str],
        offline_store: bool | None = None,
    ) -> pd.DataFrame | None:
        if len(features) == 0:
            return None

        if len(entities) == 0:
            return None

        start = time.time()

        # load features from cache
        cached_df, missing_entities = self._get_cached(entities, features)

        if len(missing_entities) == 0 and cached_df is not None:
            return cached_df.reindex(pd.DataFrame(entities).values[:, 0])

        df = (
            await self.fs.get_online_features_async(
                features=features, entity_rows=missing_entities, full_feature_names=True
            )
        ).to_df()

        # ingest into offline store
        if (offline_store or self.offline_store) and len(df) > 0:
            if self.background_tasks is None:
                logger.warning(
                    "Missing background task manager: ingesting features to offline store sequentially."
                )
                self.ingest_to_offline_store(df, event_time)
            else:
                self.background_tasks.add_task(
                    self.ingest_to_offline_store, df, event_time
                )

        # drop entity columns
        columns = set(df.columns)
        df.drop(columns=[e for e in entities[0].keys() if e in columns], inplace=True)

        self._remember(missing_entities, df, features)

        if cached_df is not None:
            df.index = pd.DataFrame(missing_entities).values[:, 0]
            df = pd.concat([df, cached_df])
            df = df[~df.index.duplicated()].reindex(pd.DataFrame(entities).values[:, 0])

        logger.info(
            f"Fetched features for {len(missing_entities)} entities in {int((time.time() - start) * 1000)} milliseconds."
        )

        return df
