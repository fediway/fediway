
import random
from sqlmodel import select, Session as DBSession
from fastapi import APIRouter, Depends, Request

from modules.fediway.sources import Source
from shared.services.feed_service import FeedService
from app.api.dependencies import (
    get_trending_statuses_by_influential_accounts_source,
    get_status_feed
)
from shared.core.db import get_db_session
from app.modules.models import Tag, Status
from app.api.dependencies import get_trending_tags_sources
from app.api.items import TagItem
from app.api.items import StatusItem
from config import config

router = APIRouter()

def public_timeline_sources(
    trending_statuses_by_influential_accounts: list[Source] = Depends(get_trending_statuses_by_influential_accounts_source),
):
    return trending_statuses_by_influential_accounts

@router.get('/statuses')
async def status_trends(
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

@router.get('/tags')
async def tag_trends(
    sources = Depends(get_trending_tags_sources),
    db: DBSession = Depends(get_db_session),
) -> list[TagItem]:
    
    candidates = []
    for source in sources:
        for candidate in source.collect(10):
            candidates.append(candidate)
    
    random.shuffle(candidates)
    candidates = candidates[:10]

    tags = db.exec(select(Tag).where(Tag.id.in_(candidates))).all()

    return [TagItem(
        name=tag.name,
        url="",
    ) for tag in tags]