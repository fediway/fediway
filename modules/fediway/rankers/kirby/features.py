from feast import FeatureStore, FeatureView

LABELS = [
    "label.is_favourited",
    "label.is_reblogged",
    # 'label.is_replied',
    # 'label.is_reply_engaged_by_author',
]


def get_feature_views(feature_store: FeatureStore) -> list[FeatureView]:
    projections = feature_store.get_feature_service("kirby").feature_view_projections
    return [
        feature_store.get_feature_view(projection.name) for projection in projections
    ]
