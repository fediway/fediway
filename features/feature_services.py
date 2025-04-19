
from feast import FeatureService

from features import account_author_view

ranker_fs = FeatureService(
    name="ranker",
    features=[account_author_view]
)