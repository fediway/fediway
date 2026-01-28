from datetime import timedelta

from feast import Field
from feast.types import Float32, Int64

from ...entities import account
from ...utils import make_feature_view

feature_views = []

SPECS = ["1d", "7d", "60d"]

FEATURES = [
    Field(name="num_all", dtype=Int64),
    Field(name="num_favs", dtype=Int64),
    Field(name="num_reblogs", dtype=Int64),
    Field(name="num_replies", dtype=Int64),
    Field(name="num_poll_votes", dtype=Int64),
    Field(name="num_bookmarks", dtype=Int64),
    Field(name="num_quotes", dtype=Int64),
    Field(name="num_has_link", dtype=Int64),
    Field(name="num_has_photo_link", dtype=Int64),
    Field(name="num_has_video_link", dtype=Int64),
    Field(name="num_has_rich_link", dtype=Int64),
    Field(name="num_has_poll", dtype=Int64),
    Field(name="num_has_image", dtype=Int64),
    Field(name="num_has_gifv", dtype=Int64),
    Field(name="num_has_video", dtype=Int64),
    Field(name="num_has_audio", dtype=Int64),
    Field(name="num_has_quote", dtype=Int64),
    Field(name="avg_text_chars_count", dtype=Float32),
    Field(name="max_text_chars_count", dtype=Int64),
    Field(name="min_text_chars_count", dtype=Int64),
    Field(name="avg_text_uppercase_count", dtype=Float32),
    Field(name="max_text_uppercase_count", dtype=Int64),
    Field(name="min_text_uppercase_count", dtype=Int64),
    Field(name="avg_text_newlines_count", dtype=Float32),
    Field(name="max_text_newlines_count", dtype=Int64),
    Field(name="min_text_newlines_count", dtype=Int64),
    Field(name="avg_text_custom_emojis_count", dtype=Float32),
    Field(name="max_text_custom_emojis_count", dtype=Int64),
    Field(name="min_text_custom_emojis_count", dtype=Int64),
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
            f"account_engagement_{spec}",
            entities=[account],
            schema=FEATURES,
            online=True,
            tags={
                "online_store": f"online_features_account_engagement_{spec}",
                "offline_store": f"offline_features_account_engagement_{spec}",
            },
            ttl=timedelta(days=int(spec.replace("d", ""))),
        )
    )
