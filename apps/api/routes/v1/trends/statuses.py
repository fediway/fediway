from sqlmodel import select, Session as DBSession
from fastapi import APIRouter, Depends

from modules.fediway.feed.sampling import InverseTransformSampler
from modules.fediway.feed.pipeline import Feed
from modules.fediway.sources import Source
from apps.api.core.ranker import ranker
from apps.api.services.feed_service import FeedService
from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.statuses import (
    get_popular_by_influential_accounts_sources,
)
from shared.core.db import get_db_session
from modules.mastodon.models import Tag, Status
from modules.mastodon.items import TagItem, StatusItem
from config import config

router = APIRouter()


def statuses_trend_sources(
    popular_by_influential_accounts: list[Source] = Depends(
        get_popular_by_influential_accounts_sources
    ),
):
    return popular_by_influential_accounts


@router.get("/statuses")
async def status_trends(
    offset: int = 0,
    feed: FeedService = Depends(get_feed),
    sources=Depends(statuses_trend_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    max_candidates_per_source = config.fediway.max_candidates_per_source(len(sources))

    pipeline = (
        feed.name("trends/statuses")
        .select("status_id")
        .sources([(source, max_candidates_per_source) for source in sources])
        .rank(ranker)
        .remember()
        .diversify(by="status:account_id", penalty=0.1)
        .sample(config.fediway.feed_batch_size, sampler=InverseTransformSampler())
        .paginate(config.fediway.feed_batch_size, offset=offset)
    )

    recommendations = await feed.execute()

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]
