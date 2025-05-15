
from feast import FeatureStore

LABELS = [
    'label.is_favourited',
    'label.is_reblogged',
    # 'label.is_replied',
    # 'label.is_reply_engaged_by_author',
]

def get_feature_views(feature_store: FeatureStore):
    return feature_store.get_feature_service('kirby')._features