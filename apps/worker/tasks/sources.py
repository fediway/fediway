from shared.core.redis import get_redis
from shared.core.rw import rw_session
from shared.services.store_viral_statuses_source_service import (
    StoreViralStatusesSourceService,
)

from ..main import app


@app.task(name="sources.viral_statuses", queue="sources")
def store_viral_source_service():
    with rw_session() as rw:
        StoreViralStatusesSourceService(get_redis(), rw)()
