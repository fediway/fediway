from datetime import datetime

import numpy as np
import pandas as pd
from feast import Field, RequestSource
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Int64
from psycopg2.extensions import AsIs, register_adapter
from sqlmodel import select

from modules.mastodon.models import Status, StatusStats

# tell psycopg2 how to handle numpy types
register_adapter(np.int64, AsIs)

status_request = RequestSource(
    name="status_db_source",
    schema=[Field(name="status_id", dtype=Int64)],
)


@on_demand_feature_view(
    name="status_db",
    sources=[status_request],
    schema=[
        Field(name="account_id", dtype=Int64),
        Field(name="favourites_count", dtype=Int64),
        Field(name="reblogs_count", dtype=Int64),
        Field(name="replies_count", dtype=Int64),
        Field(name="age_in_seconds", dtype=Int64),
    ],
)
def status_db_features(status_ids: pd.DataFrame) -> pd.DataFrame:
    from shared.core.db import db_session

    with db_session() as db:
        rows = db.exec(
            select(
                Status.id,
                Status.account_id,
                Status.created_at,
                StatusStats.favourites_count,
                StatusStats.reblogs_count,
                StatusStats.replies_count,
            )
            .join(StatusStats, StatusStats.status_id == Status.id)
            .where(Status.id.in_(status_ids.values[:, 0].tolist()))
        ).all()
    rows_map = {row.id: row for row in rows}

    datetime.now()
    results = []
    zero = [0, 0, 0, 0, 0]
    for status_id in status_ids.values[:, 0]:
        if status_id not in rows_map:
            results.append(zero)
        else:
            row = rows_map[status_id]
            results.append(
                [
                    row.account_id,
                    row.favourites_count,
                    row.reblogs_count,
                    row.replies_count,
                    (datetime.now() - row.created_at).total_seconds(),
                ]
            )

    df = pd.DataFrame(
        results,
        columns=[
            "account_id",
            "favourites_count",
            "reblogs_count",
            "replies_count",
            "age_in_seconds",
        ],
    )

    return df
