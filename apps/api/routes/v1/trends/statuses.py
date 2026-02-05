from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.feeds import get_feed_engine, get_trending_statuses_feed
from apps.api.feeds import TrendingStatusesFeed
from apps.api.services.feed_engine import FeedEngine, get_request_state_key
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session

router = APIRouter()


@router.get("/statuses")
async def status_trends(
    request: Request,
    response: Response,
    offset: int = 0,
    engine: FeedEngine = Depends(get_feed_engine),
    feed: TrendingStatusesFeed = Depends(get_trending_statuses_feed),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    state_key = get_request_state_key(request)

    results = await engine.run(
        feed,
        state_key=state_key,
        flush=(offset == 0),
        offset=offset,
        limit=config.fediway.feed_batch_size,
    )

    status_ids = [r.id for r in results]

    set_next_link(request, response, {"offset": offset + len(results)})

    statuses = db.exec(Status.select_by_ids(status_ids)).all()

    return [StatusItem.from_model(status) for status in statuses]
