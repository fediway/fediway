from feast import FeatureView, Field
from feast.types import Float32, Int64, Bool, String, Array, UnixTimestamp
from datetime import timedelta

from config import config

from ...entities import status
from ...utils import make_feature_view

feature_views = []

FEATURES = [
    Field(name="favourites_count", dtype=Int64),
    Field(name="reblogs_count", dtype=Int64),
    Field(name="replies_count", dtype=Int64),
]

feature_views.append(
    make_feature_view(
        f"status_stats",
        entities=[status],
        schema=FEATURES,
        online=True,
        tags={
            "online_store": f"status_stats",
            "offline_store": f"offline_features_status_stats",
        },
        ttl=timedelta(days=30),
    )
)
