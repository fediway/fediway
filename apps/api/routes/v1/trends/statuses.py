from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession
from sqlmodel import Session as RWSession

from apps.api.dependencies.feeds import get_feed_engine
from apps.api.dependencies.lang import get_languages
from apps.api.feeds import TrendingStatusesFeed
from apps.api.services.feed_engine import FeedEngine
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session

router = APIRouter()


@router.get("/statuses")
async def status_trends(
    request: Request,
    response: Response,
    offset: int = 0,
    engine: FeedEngine = Depends(get_feed_engine),
    rw: RWSession = Depends(get_rw_session),
    redis=Depends(get_redis),
    languages: list[str] = Depends(get_languages),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    feed = TrendingStatusesFeed(
        redis=redis,
        rw=rw,
        languages=languages,
    )

    results = await engine.run(
        feed,
        flush=(offset == 0),
        offset=offset,
        limit=config.fediway.feed_batch_size,
    )

    status_ids = [r.id for r in results]

    set_next_link(request, response, {"offset": offset + len(results)})

    statuses = db.exec(Status.select_by_ids(status_ids)).all()

    return [StatusItem.from_model(status) for status in statuses]
