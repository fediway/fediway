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


class KirbyFeatureService:
    def __init__(
        self,
        feature_store: FeatureStore,
        feature_service: Features,
        account_id: int,
    ):
        self.feature_service = feature_service
        self.feature_store = feature_store
        self.account_id = account_id
        self.base_features = feature_store.get_feature_service("kirby")

    def _get_base_features(self, status_entities):
        author_ids = self.feature_service.get(
            status_entities, features=["status:account_id"]
        ).values[:, 0]
        entities = [
            status_entitiy
            | {
                "author_id": author_id,
                "account_id": self.account_id,
            }
            for status_entitiy, author_id in zip(status_entities, author_ids)
        ]
        return self.feature_store.get_online_features(
            features=self.base_features, entity_rows=entities, full_feature_names=True
        ).to_df()

    def get(self, entities: list[dict[str, int]], *pargs):
        base_features = self._get_base_features(entities)
        return base_features.fillna(0.0)
