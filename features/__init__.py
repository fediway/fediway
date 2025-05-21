from .entities import account, author, status
from .services.kirby import kirby_features
from .views.combined_status_tags import combined_status_tags_features
from .views.embedding import account_embedding_features
from .views.engagement import account_author_features, account_features, author_features
from .views.favourites import account_favourites
from .views.status import status_features

ENTITIES = [account, author, status]

FEATURE_VIEWS = (
    # account features
    account_features
    + account_embedding_features
    + [account_favourites]
    +
    # author features
    author_features
    +
    # account author features
    account_author_features
    +
    # status features
    [status_features]
    + combined_status_tags_features
)

FEATURES_SERVICES = [kirby_features]
