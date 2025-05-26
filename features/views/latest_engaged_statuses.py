from feast import FeatureView, Field
from feast.types import Int64, Array
from datetime import timedelta

from ..entities import account
from ..utils import get_push_source

latest_engaged_statuses = FeatureView(
    name="latest_engaged_statuses",
    entities=[account],
    ttl=timedelta(days=365),
    schema=[Field(name=f"status_ids", dtype=Array(Int64))],
    online=True,
    source=get_push_source(view_name="latest_engaged_statuses"),
)
