from feast import FeatureView, Field
from feast.types import Float32, Int64
from datetime import timedelta

from config import config

from ..entities import status
from ..utils import make_feature_view

account_status_features = []


def _make_engagement_fv(entities, spec: str, fields: list[str]) -> FeatureView:
    view_name = f"account_status_{spec}"

    schema = []

    for field, aggregates in fields:
        for agg in aggregates:
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
        ttl=timedelta(days=int(spec.replace("d", ""))),
    )


SPECS = ["7d", "56d"]

FEATURES = [
    ("reblogs_count", ["sum", "avg", "max"]),
    ("replies_count", ["sum", "avg", "max"]),
    ("fav_count", ["sum", "avg", "max"]),
    (
        "has_image",
        [
            "sum",
            "avg",
        ],
    ),
    (
        "has_gifv",
        [
            "sum",
            "avg",
        ],
    ),
    (
        "has_video",
        [
            "sum",
            "avg",
        ],
    ),
    (
        "has_audio",
        [
            "sum",
            "avg",
        ],
    ),
    ("num_mentions", ["sum", "avg", "max"]),
    ("num_tags", ["sum", "avg", "max"]),
    (
        "is_reblog",
        [
            "sum",
            "avg",
        ],
    ),
    (
        "is_reply",
        [
            "sum",
            "avg",
        ],
    ),
]

for spec in SPECS:
    _fv = _make_engagement_fv(entities=[status], spec=spec, fields=FEATURES)
    account_status_features.append(_fv)
