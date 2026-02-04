from .entities import (
    account,
    author,
    instance,
    preview_card,
    preview_card_domain,
    status,
    tag,
)
from .services import (
    account_author_engagement_feature_service,
    account_status_engagement_feature_service,
    account_tag_engagement_feature_service,
    status_feature_service,
)
from .views.base import status_db_features, status_features, status_stats_features
from .views.engagement import (
    account_author_engagement_features,
    account_engagement_features,
    account_instance_engagement_features,
    account_preview_card_domain_engagement_features,
    account_preview_card_engagement_features,
    account_tag_engagement_features,
    author_engagement_features,
    preview_card_domain_engagement_features,
    preview_card_engagement_features,
    tag_engagement_features,
)

ENTITIES = [account, author, status, tag, instance, preview_card, preview_card_domain]

FEATURE_VIEWS = (
    # engagement features
    account_author_engagement_features
    + account_instance_engagement_features
    + account_engagement_features
    + account_preview_card_domain_engagement_features
    + account_preview_card_engagement_features
    + account_tag_engagement_features
    + author_engagement_features
    + preview_card_domain_engagement_features
    + preview_card_engagement_features
    + tag_engagement_features
    # entities features
    + [status_db_features]
    + status_stats_features
    + status_features
)

FEATURES_SERVICES = [
    account_author_engagement_feature_service,
    account_tag_engagement_feature_service,
    account_status_engagement_feature_service,
    status_feature_service,
]
