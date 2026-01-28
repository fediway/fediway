from datetime import timedelta

from feast import Field
from feast.types import Int64

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
        "status_stats",
        entities=[status],
        schema=FEATURES,
        online=True,
        tags={
            "online_store": "status_stats",
            "offline_store": "offline_features_status_stats",
        },
        ttl=timedelta(days=30),
    )
)
