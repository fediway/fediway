
from feast import Entity, ValueType

# --- core entitites ---

account = Entity(
    name="account_id",
    value_type=ValueType.INT64,
    description="Account identifier"
)

status = Entity(
    name="status_id",
    value_type=ValueType.INT64,
    description="Status identifier"
)

# --- composite entitites ---

account_status = Entity(
    name="account_status",
    value_type=ValueType.STRING,
    join_keys=["account_id", "status_id"]
)

