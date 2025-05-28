from fastapi import APIRouter, Depends, Response, Request
from sqlmodel import Session as DBSession

from apps.api.modules.utils import set_next_link
from apps.api.core.ranker import stats_ranker
from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.statuses import (
    get_popular_by_influential_accounts_sources,
)
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.feed.sampling import InverseTransformSampler
from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session

router = APIRouter()


def statuses_trend_sources(
    popular_by_influential_accounts: list[Source] = Depends(
        get_popular_by_influential_accounts_sources
    ),
):
    return popular_by_influential_accounts


@router.get("/statuses")
async def status_trends(
    request: Request,
    response: Response,
    offset: int = 0,
    feed: FeedService = Depends(get_feed),
    sources=Depends(statuses_trend_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    max_candidates_per_source = config.fediway.max_candidates_per_source(len(sources))

    pipeline = (
        feed
        .name("trends/statuses")
        .select("status_id")
        .sources([(source, max_candidates_per_source) for source in sources])
        .rank(stats_ranker)
        .remember()
        .diversify(by="status:account_id", penalty=0.1)
        .sample(config.fediway.feed_batch_size, sampler=InverseTransformSampler())
        .paginate(config.fediway.feed_batch_size, offset=offset)
    )
    
    if offset == 0:
        feed.flush()

    recommendations = await pipeline.execute()

    set_next_link(request, response, {
        'offset': offset + len(recommendations)
    })

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]
