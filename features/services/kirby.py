
from feast import FeatureService

from ..views.engagement import (
    account_features, 
    author_features, 
    account_author_features
)

kirby_features = FeatureService(
    name="kirby",
    features=(
        account_features + 
        author_features + 
        account_author_features
    )
)