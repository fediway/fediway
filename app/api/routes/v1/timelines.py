
from sqlmodel import Session as DBSession
from fastapi import APIRouter, Depends, Request, BackgroundTasks

from modules.fediway.sources import Source
from app.core.db import get_db_session
from app.api.dependencies import get_new_statuses_by_language_source
from app.api.items import StatusItem
from app.services.feed_service import FeedService, get_feed_service
from app.modules.models import Status
from app.api.items import StatusItem
from config import config

router = APIRouter()

def get_public_sources(
    new_statuses_by_language: list[Source] = Depends(get_new_statuses_by_language_source)
):
    return new_statuses_by_language

@router.get('/public')
async def public_timeline(
    request: Request,
    tasks: BackgroundTasks,
    feed: FeedService = Depends(get_feed_service(name='home')),
    sources: list[Source] = Depends(get_public_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:

    feed.load_or_create()
    feed.set_sources(sources)
    recommendations = feed.get_recommendations(config.fediway.feed_samples_page_size)

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]