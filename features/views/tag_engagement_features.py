from feast import FeatureView, Field
from feast.types import Float32, Int64
from datetime import timedelta

from config import config

from ..entities import tag
from ..utils import make_feature_view

tag_engagement_features = []

SPECS = ["1d", "7d", "60d"]

FEATURES = [
    "num_engagers",
    "num_authors",
    "num_statuses",
    "fav_count",
    "reblogs_count",
    "replies_count",
    "num_images",
    "num_gifvs",
    "num_videos",
    "num_audios",
]


def _make_fv(entities, spec: str, fields: list[str]) -> FeatureView:
    view_name = f"tag_engagement_all_{spec}"

    schema = []

    for field in fields:
        schema.append(
            Field(
                name=field,
                dtype=Int64,
            )
        )

    return make_feature_view(
        view_name,
        entities=entities,
        schema=schema,
        online=True,
        ttl=timedelta(days=int(spec.replace("d", ""))),
    )


for spec in SPECS:
    _fv = _make_fv(entities=[tag], spec=spec, fields=FEATURES)
    tag_engagement_features.append(_fv)
