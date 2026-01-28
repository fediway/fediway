from feast import FeatureService

from .views.base import status_features, status_stats_features
from .views.engagement import (
    account_author_engagement_features,
    account_instance_engagement_features,
    account_engagement_features,
    account_preview_card_domain_engagement_features,
    account_preview_card_engagement_features,
    account_tag_engagement_features,
    author_engagement_features,
    preview_card_domain_engagement_features,
    preview_card_engagement_features,
    tag_engagement_features,
)

account_author_engagement_feature_service = FeatureService(
    name="account_author_engagement_features",
    features=(account_author_engagement_features),
)

account_tag_engagement_feature_service = FeatureService(
    name="account_tag_engagement_features",
    features=(account_tag_engagement_features + tag_engagement_features),
)

account_status_engagement_feature_service = FeatureService(
    name="account_status_engagement_features",
    features=(
        account_author_engagement_features
        + account_instance_engagement_features
        + account_engagement_features
        + account_preview_card_domain_engagement_features
        + account_preview_card_engagement_features
        + author_engagement_features
        + preview_card_domain_engagement_features
        + preview_card_engagement_features
    ),
)

status_feature_service = FeatureService(
    name="status_features",
    features=(status_stats_features + status_features),
)
