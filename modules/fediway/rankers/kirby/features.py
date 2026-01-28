import asyncio

import numpy as np
import pandas as pd
from feast import FeatureStore, FeatureView

from modules.fediway.feed import Features

LABELS = [
    "label.is_favourited",
    "label.is_reblogged",
    "label.is_replied",
    "label.is_reply_engaged_by_author",
]


def get_feature_views(feature_store: FeatureStore) -> list[FeatureView]:
    projections = feature_store.get_feature_service("kirby").feature_view_projections
    return [feature_store.get_feature_view(projection.name) for projection in projections]


def _is_none_or_nan(value):
    if value is None:
        return True
    try:
        return np.isnan(value)
    except TypeError:
        return False


class KirbyFeatureService(Features):
    def __init__(
        self,
        feature_store: FeatureStore,
        feature_service: Features,
        account_id: int,
    ):
        self.feature_service = feature_service
        self.feature_store = feature_store
        self.account_id = account_id
        self.account_author_engagement_features = feature_store.get_feature_service(
            "account_author_engagement_features"
        )
        self.account_status_engagement_features = feature_store.get_feature_service(
            "account_status_engagement_features"
        )
        self.account_tag_engagement_features = feature_store.get_feature_service(
            "account_tag_engagement_features"
        )
        self.status_features = feature_store.get_feature_service("status_features")

    async def _get_account_tag_features(self, status_entities, statuses):
        status_tags = statuses["status__tags"].values

        status_ids = []
        entities = []
        for status_entitiy, tags in zip(status_entities, status_tags):
            for tag_id in (tags or [])[:15]:  # at max 15 tags
                if tag_id is None:
                    continue
                status_ids.append(status_entitiy["status_id"])
                entities.append(
                    {
                        "tag_id": tag_id,
                        "account_id": self.account_id,
                    }
                )

        if len(entities) == 0:
            return

        df = await self.feature_service.get(
            entities=entities,
            features=self.account_tag_engagement_features,
        )

        df["status_id"] = status_ids

        df = pd.merge(
            pd.DataFrame(status_entities),
            df.groupby("status_id").mean(),
            on="status_id",
            how="left",
        ).drop(columns=["status_id"])

        return df

    async def _get_account_mentions_features(self, status_entities, statuses):
        status_mentions = statuses["status__mentions"].values

        status_ids = []
        entities = []
        for status_entitiy, mentions in zip(status_entities, status_mentions):
            for mention in (mentions or [])[:10]:  # at max 10 mentions
                if mention is None:
                    continue
                status_ids.append(status_entitiy["status_id"])
                entities.append(
                    {
                        "author_id": mention,
                        "account_id": self.account_id,
                    }
                )

        if len(entities) == 0:
            return

        df = await self.feature_service.get(
            entities=entities,
            features=self.account_author_engagement_features,
        )

        df["status_id"] = status_ids

        df = pd.merge(
            pd.DataFrame(status_entities),
            df.groupby("status_id").mean(),
            on="status_id",
            how="left",
        ).drop(columns=["status_id"])

        return df

    async def _get_account_status_features(self, status_entities, statuses):
        entities = statuses[
            [
                "status__author_id",
                # "status__author_domain",
                "status__preview_card_id",
                "status__preview_card_domain",
            ]
        ].values

        entities = []
        status_ids = []

        for status_entitiy, (
            author_id,
            # author_domain,
            preview_card_id,
            preview_card_domain,
        ) in zip(status_entities, entities):
            if _is_none_or_nan(author_id):
                continue
            if _is_none_or_nan(preview_card_id):
                continue
            if _is_none_or_nan(preview_card_domain):
                continue

            status_ids.append(status_entity["status_id"])
            entities.append(
                [
                    status_entitiy
                    | {
                        "author_id": author_id,
                        "domain": "",
                        "preview_card_id": preview_card_id,
                        "preview_card_domain": preview_card_domain,
                        "account_id": self.account_id,
                    }
                ]
            )

        if len(entities) == 0:
            return

        df = await self.feature_service.get(
            entities=entities,
            features=self.account_status_engagement_features,
        )

        df["status_id"] = status_ids

        df = pd.merge(
            pd.DataFrame(status_entities),
            df,
            on="status_id",
            how="left",
        ).drop(columns=["status_id"])

        return df

    async def get(self, entities: list[dict[str, int]], *pargs, **kwargs):
        statuses = await self.feature_service.get(entities, features=self.status_features)

        features = await asyncio.gather(
            self._get_account_status_features(entities, statuses),
            self._get_account_mentions_features(entities, statuses),
            self._get_account_tag_features(entities, statuses),
        )

        df = pd.concat([statuses] + [f for f in features if f is not None], axis=1)

        return df
