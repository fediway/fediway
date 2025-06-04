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
    ("reblogs_count", ["sum", "avg", "stddev_pop", "max"]),
    ("replies_count", ["sum", "avg", "stddev_pop", "max"]),
    ("fav_count", ["sum", "avg", "stddev_pop", "max"]),
    (
        "has_image",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
    (
        "has_gifv",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
    (
        "has_video",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
    (
        "has_audio",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
    ("num_mentions", ["sum", "avg", "stddev_pop", "max"]),
    ("num_tags", ["sum", "avg", "stddev_pop", "max"]),
    (
        "is_reblog",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
    (
        "is_reply",
        [
            "sum",
            "avg",
            "stddev_pop",
        ],
    ),
]

for spec in SPECS:
    _fv = _make_engagement_fv(entities=[status], spec=spec, fields=FEATURES)
    account_status_features.append(_fv)
