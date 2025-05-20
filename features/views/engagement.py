from feast import FeatureView, Field
from feast.types import Int64

from config import config
from ..utils import make_feature_view
from ..entities import account, author

author_features = []
account_features = []
account_author_features = []

GROUPS = [
    ("account", [account], ["1d", "7d", "30d"]),
    ("author", [author], ["1d", "7d", "30d"]),
    ("account_author", [account, author], ["30d"]),
]

FEATURES = [
    {
        "infix": "engagement",
        "types": ["all"],
        "fields": [
            "fav_count",
            "reblogs_count",
            "replies_count",
            "num_images",
            "num_gifvs",
            "num_videos",
            "num_audios",
        ],
    },
    {
        "infix": "engagement_is",
        "types": ["favourite", "reblog", "reply"],
        "fields": ["num_images", "num_gifvs", "num_videos", "num_audios"],
    },
    {
        "infix": "engagement_has",
        "types": ["image", "gifv", "video"],
        "fields": ["fav_count", "reblogs_count", "replies_count"],
    },
]


def _make_engagement_fv(
    group, entities, spec: str, infix: str, engagement_type: str, fields: list[str]
) -> FeatureView:
    view_name = f"{group}_{infix}_{engagement_type}_{spec}"

    schema = []

    for field in fields:
        schema.append(Field(name=f"{field}_{spec}", dtype=Int64))

    return make_feature_view(
        view_name,
        entities=entities,
        schema=schema,
        offline_store_path=config.feast.feast_offline_store_path,
        online=True,
    )


for group, entities, specs in GROUPS:
    for feats in FEATURES:
        for engagement_type in feats["types"]:
            for spec in specs:
                _fv = _make_engagement_fv(
                    group,
                    entities=entities,
                    spec=spec,
                    engagement_type=engagement_type,
                    infix=feats["infix"],
                    fields=feats["fields"],
                )

                if group == "account":
                    account_features.append(_fv)
                if group == "author":
                    author_features.append(_fv)
                if group == "account_author":
                    account_author_features.append(_fv)
