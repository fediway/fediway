from feast import FeatureView, Field
from feast.types import Float32, Int64
from datetime import timedelta

from config import config

from ...entities import account, preview_card
from ...utils import make_feature_view

feature_views = []

SPECS = ["1d", "7d", "60d"]

FEATURES = [
    Field(name="num_all", dtype=Int64),
    Field(name="num_domains", dtype=Int64),
    Field(name="num_favs", dtype=Int64),
    Field(name="num_reblogs", dtype=Int64),
    Field(name="num_replies", dtype=Int64),
    Field(name="num_poll_votes", dtype=Int64),
    Field(name="num_bookmarks", dtype=Int64),
    Field(name="num_links", dtype=Int64),
    Field(name="num_photo_links", dtype=Int64),
    Field(name="num_video_links", dtype=Int64),
    Field(name="num_rich_links", dtype=Int64),
    Field(name="num_polls", dtype=Int64),
    Field(name="num_images", dtype=Int64),
    Field(name="num_gifvs", dtype=Int64),
    Field(name="num_videos", dtype=Int64),
    Field(name="num_audios", dtype=Int64),
    Field(name="avg_status_fav_count", dtype=Float32),
    Field(name="max_status_fav_count", dtype=Int64),
    Field(name="min_status_fav_count", dtype=Int64),
    Field(name="avg_status_reblogs_count", dtype=Float32),
    Field(name="max_status_reblogs_count", dtype=Int64),
    Field(name="min_status_reblogs_count", dtype=Int64),
    Field(name="avg_status_replies_count", dtype=Float32),
    Field(name="max_status_replies_count", dtype=Int64),
    Field(name="min_status_replies_count", dtype=Int64),
    Field(name="avg_mentions", dtype=Float32),
    Field(name="avg_tags", dtype=Float32),
]

for spec in SPECS:
    feature_views.append(
        make_feature_view(
            f"account_preview_card_engagement_{spec}",
            entities=[account, preview_card],
            schema=FEATURES,
            online=True,
            tags={"push": "kafka"},
            ttl=timedelta(days=int(spec.replace("d", ""))),
        )
    )
