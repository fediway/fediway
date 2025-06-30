from .entities import account, author, status, tag

# from .services.kirby import kirby_features
# from .views.account_status import account_status_features
# from .views.combined_status_tags import combined_status_tags_features
# from .views.embedding import account_embedding_features
# from .views.engagement import account_author_features, account_features, author_features
from .views.status import status_features

# from .views.latest_engaged_statuses import latest_engaged_statuses
from .views.tag_engagement_features import tag_engagement_features

ENTITIES = [account, author, status, tag]

FEATURE_VIEWS = (
    # tag features
    tag_engagement_features
    # # account features
    # account_features
    # + account_status_features
    # + account_embedding_features
    # + [latest_engaged_statuses]
    # +
    # # author features
    # author_features
    # +
    # # account author features
    # account_author_features
    # +
    # status features
    + [status_features]
    # + combined_status_tags_features
)

FEATURES_SERVICES = [
    # kirby_features
]
