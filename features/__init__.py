from .entities import (
    account,
    author,
    status,
    tag,
    domain,
    preview_card,
    preview_card_domain,
)

from .views.engagement import (
    account_author_engagement_features,
    account_domain_engagement_features,
    account_engagement_features,
    account_preview_card_domain_engagement_features,
    account_preview_card_engagement_features,
    account_tag_engagement_features,
    author_engagement_features,
    preview_card_domain_engagement_features,
    preview_card_engagement_features,
    tag_engagement_features,
)
from .views.base import status_db_features, status_stats_features, status_features

from .services import (
    account_author_engagement_feature_service,
    account_tag_engagement_feature_service,
    account_status_engagement_feature_service,
    status_feature_service,
)

ENTITIES = [account, author, status, tag, domain, preview_card, preview_card_domain]

FEATURE_VIEWS = (
    # engagement features
    account_author_engagement_features
    + account_domain_engagement_features
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
