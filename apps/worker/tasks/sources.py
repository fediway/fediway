from shared.services.store_popular_by_influential_accounts_source_service import (
    StorePouplarByInfluentialAccountsSourceService,
)
from shared.services.store_viral_source_service import (
    StoreViralSourceService,
)

from shared.core.rw import rw_session
from shared.core.redis import get_redis
from shared.core.schwarm import driver

from ..main import app


@app.task(name="sources.viral", queue="sources")
def store_unusual_popularity_source():
    with rw_session() as rw:
        StoreViralSourceService(get_redis(), rw)()


@app.task(name="sources.popular_by_influential_accounts", queue="sources")
def store_popular_by_influential_accounts_source():
    StorePouplarByInfluentialAccountsSourceService(get_redis(), driver)()
