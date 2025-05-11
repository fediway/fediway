
from sqlmodel import Session as DBSession
from fastapi import APIRouter, Depends, Request, BackgroundTasks

from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status

from shared.core.db import get_db_session

from apps.api.services.feed_service import FeedService
from apps.api.dependencies.feeds import get_feed
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
    feed: FeedService = Depends(get_feed),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:

    pipeline = (
        feed
        .name('timelines/public')
        .select('status_id')
        .sources([(source, max_candidates_per_source) for source in sources])
        .rank(ranker)
        .diversify(by='status:account_id', penalty=0.1)
        .sample(config.fediway.feed_batch_size)
        .paginate(config.fediway.feed_batch_size, offset=0)
    )

    recommendations = await feed.execute()

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]

def public_timeline_sources(
    # hot_statuses_by_language: list[Source] = Depends(get_hot_statuses_by_language_source)
    trending_statuses_by_influential_accounts: list[Source] = Depends(get_trending_statuses_by_influential_accounts_source),
    # collaborative_filtering: list[Source] = Depends(get_collaborative_filtering_source),
):
    # return collaborative_filtering
    return trending_statuses_by_influential_accounts

@router.get('/home')
async def home_timeline(
    request: Request,
    feed: FeedService = Depends(get_feed),
    sources = Depends(public_timeline_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:

    pipeline = (
        feed
        .name('timelines/home')
        .select('status_id')
        .sources([(source, max_candidates_per_source) for source in sources])
        .rank(ranker)
        .diversify(by='status:account_id', penalty=0.1)
        .sample(config.fediway.feed_batch_size)
        .paginate(config.fediway.feed_batch_size, offset=0)
    )

    recommendations = await feed.execute()

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]