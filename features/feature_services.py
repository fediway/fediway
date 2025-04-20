
from feast import FeatureService

from features import account_features, author_features, account_author_features

ranker_fs = FeatureService(
    name="ranker",
    features=account_features + author_features + account_author_features
)