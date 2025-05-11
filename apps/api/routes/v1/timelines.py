
from sqlmodel import Session as DBSession
from fastapi import APIRouter, Depends, Request, BackgroundTasks

from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status

from shared.core.db import get_db_session

from apps.api.services.feed_service import FeedService
from apps.api.dependencies.feeds import get_status_feed
from apps.api.dependencies.sources import (
    get_hot_statuses_by_language_source, 
    get_trending_statuses_by_influential_accounts_source,
    get_collaborative_filtering_source,
)

from config import config

router = APIRouter()

def public_timeline_sources(
    # hot_statuses_by_language: list[Source] = Depends(get_hot_statuses_by_language_source)
    trending_statuses_by_influential_accounts: list[Source] = Depends(get_trending_statuses_by_influential_accounts_source),
    # collaborative_filtering: list[Source] = Depends(get_collaborative_filtering_source),
):
    # return collaborative_filtering
    return trending_statuses_by_influential_accounts

@router.get('/public')
async def public_timeline(
    request: Request,
    feed: FeedService = Depends(get_status_feed(name='timelines/public')),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:

    # statuses = (
    #     feed.name('public')
    #     .rank_by()
    #     .filter(~Post.is_sensitive)
    #     .aggregate()
    #     .diversify(
    #         by='status:account_id',
    #         strategy="round_robin"
    #     )
    #     .paginate()
    # )

    await feed.init()

    recommendations = feed.get_recommendations(config.fediway.feed_batch_size)
    statuses = db.exec(Status.select_by_ids([r.item for r in recommendations])).all()

    return [StatusItem.from_model(status) for status in statuses]

@router.get('/home')
async def home_timeline(
    request: Request,
    feed: FeedService = Depends(get_status_feed(name='timelines/public')),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    await feed.init()

    recommendations = feed.get_recommendations(config.fediway.feed_batch_size)
    statuses = db.exec(Status.select_by_ids([r.item for r in recommendations])).all()

    return [StatusItem.from_model(status) for status in statuses]