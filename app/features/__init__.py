
from .entities import account, author, status
from .views.engagement import account_features, author_features, account_author_features
from .views.embedding import account_embedding_features
from .views.meta import status_meta_features
from .services.ranker import ranker_features

ENTITIES = [account, author, status]

FEATURE_VIEWS = (
    account_features +
    author_features +
    account_author_features +
    account_embedding_features +
    [status_meta_features]
)

FEATURES_SERVICES = [
    ranker_features
]

