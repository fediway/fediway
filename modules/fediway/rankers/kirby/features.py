
from feast import FeatureStore

FEATURE_VIEWS = [
    'author_engagement_all',
    'author_engagement_is_favourite',
    'author_engagement_is_reblog',
    'author_engagement_is_reply',
    'author_engagement_has_image',
    'author_engagement_has_gifv',
    'author_engagement_has_video',
    'account_engagement_all',
    'account_engagement_is_favourite',
    'account_engagement_is_reblog',
    'account_engagement_is_reply',
    'account_engagement_has_image',
    'account_engagement_has_gifv',
    'account_engagement_has_video',
    'account_author_engagement_all',
    'account_author_engagement_is_favourite',
    'account_author_engagement_is_reblog',
    'account_author_engagement_is_reply',
    'account_author_engagement_has_image',
    'account_author_engagement_has_gifv',
    'account_author_engagement_has_video',
]

def get_feature_views(feature_store: FeatureStore):
    return [feature_store.get_feature_view(fv) for fv in FEATURE_VIEWS]