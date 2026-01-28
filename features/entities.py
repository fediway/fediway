from feast import Entity, ValueType

account = Entity(name="account_id", value_type=ValueType.INT64, description="Account identifier")

author = Entity(name="author_id", value_type=ValueType.INT64, description="Author identifier")

status = Entity(name="status_id", value_type=ValueType.INT64, description="Status identifier")

tag = Entity(name="tag_id", value_type=ValueType.INT64, description="Tag identifier")

instance = Entity(
    name="instance", value_type=ValueType.STRING, description="Fediverse instance identifier"
)

preview_card = Entity(
    name="preview_card_id", value_type=ValueType.INT64, description="Tag identifier"
)

preview_card_domain = Entity(
    name="preview_card_domain",
    value_type=ValueType.STRING,
    description="Preview card domain identifier",
)
