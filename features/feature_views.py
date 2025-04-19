
from feast import FeatureView, Field, FileSource, ValueType
from datetime import timedelta

from .entities import account, status

account_activity_view = FeatureView(
    name="account_activity",
    entities=[account],
    features=[
        Field(name="total_mentions_7d", dtype=ValueType.INT64),
    ],
    ttl=timedelta(days=31),
    batch_source=FileSource(...)
)

status_performance_view = FeatureView(
    name="status_performance",
    entities=[status],
    features=[
        Field(name="has_image", dtype=ValueType.BOOL),
    ],
    ttl=timedelta(days=8),
    batch_source=FileSource(...)
)

# --- Relationship Features ---

social_graph_view = FeatureView(
    name="social_graph",
    entities=[relationship],
    features=[
        Field(name="interaction_count_30d", dtype=Int64),
        Field(name="last_interaction", dtype=UnixTimestamp)
    ],
    ttl=timedelta(days=31),
    batch_source=FileSource(...)
)