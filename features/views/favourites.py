from feast import RequestSource, Field
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Int64, Array

from sqlmodel import select, desc
import pandas as pd

from modules.mastodon.models import Favourite

account_favourites_request = RequestSource(
    name="account_favourites_source",
    schema=[Field(name="account_id", dtype=Int64)],
)


@on_demand_feature_view(
    name="account_favourites",
    sources=[account_favourites_request],
    schema=[
        Field(name="favourites", dtype=Array(Int64)),
    ],
)
def account_favourites(account_ids: pd.DataFrame) -> pd.DataFrame:
    from shared.core.db import db_session

    results = []
    with db_session() as db:
        for account_id in account_ids.values[:, 0]:
            favourites = db.exec(
                select(Favourite.status_id)
                .where(Favourite.account_id == int(account_id))
                .order_by(desc(Favourite.id))
                .limit(20)
            ).all()
            results.append(favourites)

    df = pd.DataFrame({"favourites": results})

    return df
