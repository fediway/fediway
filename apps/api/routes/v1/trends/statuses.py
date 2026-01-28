from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.statuses import (
    get_viral_statuses_source,
)
from apps.api.utils import set_next_link
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.feed.sampling import InverseTransformSampler
from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session

router = APIRouter()


def statuses_trend_sources(
    viral_statuses: list[Source] = Depends(get_viral_statuses_source),
):
    return viral_statuses


@router.get("/statuses")
async def status_trends(
    request: Request,
    response: Response,
    offset: int = 0,
    feed: FeedService = Depends(get_feed),
    sources=Depends(statuses_trend_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    pipeline = (
        feed.name("trends/statuses")
        .select("status_id")
        .sources([(source, 50) for source in sources])
        .remember()
        .diversify(by="status:author_id", penalty=0.1)
        .sample(config.fediway.feed_batch_size, sampler=InverseTransformSampler())
        .paginate(config.fediway.feed_batch_size, offset=offset)
    )

    if offset == 0:
        feed.flush()

    recommendations = await pipeline.execute()
    status_ids = [r.id for r in recommendations]

    set_next_link(request, response, {"offset": offset + len(recommendations)})

    statuses = db.exec(Status.select_by_ids(status_ids)).all()

    return [StatusItem.from_model(status) for status in statuses]
