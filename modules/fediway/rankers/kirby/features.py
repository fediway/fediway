import asyncio
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
    return [
        feature_store.get_feature_view(projection.name) for projection in projections
    ]


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
            "account_status_engagement_features"
        )
        self.status_features = feature_store.get_feature_service("status_features")

    async def _get_tag_features(self, status_entities):
        status_tags = status_meta["status_meta__tags"].values

        entities = []
        for status_entitiy, tags in zip(status_entities, status_tags):
            for mention in tags:
                entites.append(
                    status_entitiy
                    | {
                        "tag_id": mention,
                        "account_id": self.account_id,
                    }
                )

        df = self.feature_service.get(
            entities=entities,
            features=self.account_tag_engagement_features,
        ).to_df()

        return df.group_by("status_id").mean()

    async def _get_account_mentions_features(self, status_entities, status_meta):
        mentions = status_meta["status_meta__mentions"].values

        entities = []
        for status_entitiy, group in zip(status_entities, mentions):
            for mention in group:
                entites.append(
                    status_entitiy
                    | {
                        "author_id": mention,
                        "account_id": self.account_id,
                    }
                )

        df = self.feature_service.get(
            entities=entities,
            features=self.account_author_engagement_features,
        ).to_df()

        return df.group_by("status_id").mean()

    async def _get_account_status_features(self, status_entities, status_meta):
        author_ids = status_meta["status_meta__author_id"].values

        entities = [
            status_entitiy
            | {
                "author_id": author_id,
                "account_id": self.account_id,
            }
            for status_entitiy, author_id in zip(status_entities, author_ids)
        ]

        return self.feature_service.get(
            entities=entities,
            features=self.account_status_engagement_features,
        ).to_df()

    async def get(self, entities: list[dict[str, int]], *pargs, **kwargs):
        status_meta = await self.feature_service.get(
            status_entities, features=self.status_features
        )

        account_status_features = self._get_account_status_features(
            entities, status_meta
        )
        account_mentions_features = self._get_account_mentions_features(
            entities, status_meta
        )
        account_tag_features = self._get_account_tag_features(entities, status_meta)

        asyncio.gather(
            [account_status_features, account_mentions_features, account_tag_features]
        )

        features = pd.concat(
            [
                status_meta,
                account_status_features,
                account_mentions_features,
                account_tag_features,
            ]
        )

        return features.fillna(0.0)
