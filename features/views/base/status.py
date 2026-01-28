from datetime import timedelta

from feast import Field
from feast.types import Array, Bool, Int64, String

from ...entities import status
from ...utils import make_feature_view

feature_views = []

FEATURES = [
    Field(name="author_id", dtype=Int64),
    Field(name="author_instance", dtype=String),
    # Field(name="created_at", dtype=UnixTimestamp),
    Field(name="is_reblog", dtype=Bool),
    Field(name="is_reply", dtype=Bool),
    Field(name="sensitive", dtype=Bool),
    Field(name="visibility", dtype=Bool),
    Field(name="has_link", dtype=Bool),
    Field(name="has_photo_link", dtype=Bool),
    Field(name="has_video_link", dtype=Bool),
    Field(name="has_rich_link", dtype=Bool),
    Field(name="preview_card_id", dtype=Int64),
    Field(name="preview_card_domain", dtype=String),
    Field(name="has_poll", dtype=Bool),
    Field(name="num_poll_options", dtype=Int64),
    Field(name="allows_multiple_poll_options", dtype=Bool),
    Field(name="hides_total_poll_options", dtype=Bool),
    Field(name="poll_id", dtype=Int64),
    Field(name="has_image", dtype=Bool),
    Field(name="has_gifv", dtype=Bool),
    Field(name="has_video", dtype=Bool),
    Field(name="has_audio", dtype=Bool),
    Field(name="num_media_attachments", dtype=Int64),
    Field(name="media_attachments", dtype=Array(Int64)),
    Field(name="num_mentions", dtype=Int64),
    Field(name="mentions", dtype=Array(Int64)),
    Field(name="num_tags", dtype=Int64),
    Field(name="tags", dtype=Array(Int64)),
]

feature_views.append(
    make_feature_view(
        "status",
        entities=[status],
        schema=FEATURES,
        online=True,
        tags={"online_store": "statuses", "online_store_format": "debezium"},
        ttl=timedelta(days=30),
    )
)
