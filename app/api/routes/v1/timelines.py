
from sqlmodel import Session as DBSession
from fastapi import APIRouter, Depends, Request, BackgroundTasks

from modules.fediway.sources import Source
from app.core.db import get_db_session
from app.api.dependencies import (
    get_hot_statuses_by_language_source, 
    get_trending_statuses_by_influential_accounts_source,
    get_status_feed
)
from app.api.items import StatusItem
from app.services.feed_service import FeedService
from app.modules.models import Status
from app.api.items import StatusItem
from config import config

router = APIRouter()

def public_timeline_sources(
    # hot_statuses_by_language: list[Source] = Depends(get_hot_statuses_by_language_source)
    trending_statuses_by_influential_accounts: list[Source] = Depends(get_trending_statuses_by_influential_accounts_source)
):
    return trending_statuses_by_influential_accounts

@router.get('/public')
async def public_timeline(
    request: Request,
    feed: FeedService = Depends(get_status_feed(
        name='public',
        heuristics=config.fediway.feed_heuristics,
        sources=public_timeline_sources
    )),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    await feed.init()

    recommendations = feed.get_recommendations(config.fediway.feed_batch_size)
    statuses = db.exec(Status.select_by_ids([r.item for r in recommendations])).all()

    return [StatusItem.from_model(status) for status in statuses]