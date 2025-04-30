
from feast import Entity, ValueType

account = Entity(
    name="account_id",
    value_type=ValueType.INT64,
    description="Account identifier"
)

author = Entity(
    name="author_id",
    value_type=ValueType.INT64,
    description="Author identifier"
)

status = Entity(
    name="status_id",
    value_type=ValueType.INT64,
    description="Status identifier"
)