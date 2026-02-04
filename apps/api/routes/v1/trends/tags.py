from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession
from sqlmodel import Session as RWSession
from sqlmodel import select

from apps.api.dependencies.feeds import get_feed_engine
from apps.api.feeds import TrendingTagsFeed
from apps.api.services.feed_engine import FeedEngine, get_request_state_key
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import TagItem
from modules.mastodon.models import Tag
from shared.core.db import get_db_session
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session

router = APIRouter()


@router.get("/tags")
async def tag_trends(
    request: Request,
    response: Response,
    offset: int = 0,
    engine: FeedEngine = Depends(get_feed_engine),
    rw: RWSession = Depends(get_rw_session),
    redis=Depends(get_redis),
    db: DBSession = Depends(get_db_session),
) -> list[TagItem]:
    state_key = get_request_state_key(request)

    feed = TrendingTagsFeed(redis=redis, rw=rw)

    results = await engine.run(
        feed,
        state_key=state_key,
        flush=(offset == 0),
        offset=offset,
        limit=config.fediway.feed_batch_size,
    )

    tag_ids = [r.id for r in results]

    if not tag_ids:
        return []

    set_next_link(request, response, {"offset": offset + len(results)})

    tags = db.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()

    return [TagItem.from_model(tag) for tag in tags]
