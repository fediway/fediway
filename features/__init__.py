
from .entities import account, author, status
from .views.engagement import account_features, author_features, account_author_features
from .views.embedding import account_embedding_features
from .views.status import status_features
from .views.favourites import account_favourites
from .services.kirby import kirby_features

ENTITIES = [account, author, status]

FEATURE_VIEWS = (
    account_features +
    author_features +
    account_author_features +
    account_embedding_features +
    [status_features] +
    [account_favourites]
)

FEATURES_SERVICES = [
    kirby_features
]

