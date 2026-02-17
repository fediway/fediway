from shared.core.redis import get_redis
from shared.core.rw import rw_session
from shared.services.store_trending_statuses_source_service import (
    StoreTrendingStatusesSourceService,
)
from shared.services.store_trending_tags_source_service import (
    StoreTrendingTagsSourceService,
)

from ..main import app


@app.task(name="sources.trending_statuses", queue="sources")
def store_trending_source_service():
    with rw_session() as rw:
        StoreTrendingStatusesSourceService(get_redis(), rw)()


@app.task(name="sources.trending_tags", queue="sources")
def store_trending_tags_source_service():
    with rw_session() as rw:
        StoreTrendingTagsSourceService(get_redis(), rw)()
