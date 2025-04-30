
from feast import FeatureService

from ..views.engagement import (
    account_features, 
    author_features, 
    account_author_features
)

ranker_features = FeatureService(
    name="ranker",
    features=(
        account_features + 
        author_features + 
        account_author_features
    )
)