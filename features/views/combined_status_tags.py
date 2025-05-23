from feast import FeatureView, Field
from feast.types import Float32, Int64

from config import config

from ..entities import status
from ..utils import make_feature_view

combined_status_tags_features = []


def _make_engagement_fv(entities, spec: str, fields: list[str]) -> FeatureView:
    view_name = f"combined_status_tag_engagement_all_{spec}"

    schema = []

    for agg in ["max", "sum", "avg"]:
        for field in fields:
            schema.append(
                Field(
                    name=f"{agg}_{field}_{spec}",
                    dtype=Float32 if agg == "avg" else Int64,
                )
            )

    return make_feature_view(
        view_name,
        entities=entities,
        schema=schema,
        online=True,
    )


SPECS = ["1d", "7d", "56d"]

FEATURES = [
    "fav_count",
    "reblogs_count",
    "replies_count",
    "num_images",
    "num_gifvs",
    "num_videos",
    "num_audios",
]

for spec in SPECS:
    _fv = _make_engagement_fv(entities=[status], spec=spec, fields=FEATURES)

    combined_status_tags_features.append(_fv)
