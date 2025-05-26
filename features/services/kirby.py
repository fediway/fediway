from feast import FeatureService

from ..views.combined_status_tags import combined_status_tags_features
from ..views.engagement import (
    account_author_features,
    account_features,
    author_features,
)

kirby_features = FeatureService(
    name="kirby",
    features=(
        account_features + author_features + account_author_features
        # + combined_status_tags_features
    ),
)
