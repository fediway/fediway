
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Request, 
    BackgroundTasks
)
from sqlmodel import Session as DBSession, select, func, desc
from sqlalchemy.orm import selectinload
from datetime import timedelta

from app.services.feed_service import FeedService, get_feed_service

from app.settings import settings
from app.core.db import get_db_session
from app.core.lang import get_languages
from app.core.feed import get_samples
from app.modules.session import Session
from app.modules.feed import Feed
from app.modules.models import (
    Account,
    AccountStats,
    Status, 
    StatusStats, 
    MediaAttachment, 
    PreviewCard, 
    PreviewCardStatus
)
from app.modules.sources import DatabaseSource
from app.modules.heuristics import (
    DiversifyAccountsHeuristic
)
from app.api.items import StatusItem

from app.modules.sources import (
    Source, 
    HotStatusesInALanguageSource
)

router = APIRouter()

def get_sources(session: Session, db: DBSession) -> list[Source]:
    sources = []

    for lang in get_languages(session):
        source = HotStatusesInALanguageSource(
            language=lang,
            max_age=timedelta(days=settings.feed_max_age_in_days),
            db=db
        )
        sources.append(source)

    return sources

def load_status_items(status_ids: list[str], db: DBSession, load_reblogs: bool = True) -> list[StatusItem]:
    statuses = db.exec((
        select(Status)
        .options(selectinload(Status.account).subqueryload(Account.stats))
        .options(selectinload(Status.preview_card))
        .options(selectinload(Status.stats))
        .options((
            selectinload(Status.reblog)
            .options(selectinload(Status.media_attachments))
            .options(selectinload(Status.stats))
            .options(selectinload(Status.preview_card))))
        .options(selectinload(Status.media_attachments))
        .where(Status.id.in_(status_ids))
    )).all()

    return [StatusItem.from_model(status) for status in statuses]

@router.get("/test",)
async def test() -> str:
    return "Hello World!"

@router.get('/timelines/public')
async def public_timeline(
    request: Request,
    tasks: BackgroundTasks,
    feed: FeedService = Depends(get_feed_service(name='home')),
    db: Session = Depends(get_db_session),
) -> list[StatusItem]:
    
    feed.load_or_create()
    feed.set_sources(get_sources(request.state.session, db))
    recommendations = feed.get_recommendations(settings.feed_samples_page_size)

    items = load_status_items(recommendations, db)

    print("seen", feed.feed.seen_ids)

    return items

@router.get('/timelines/home')
async def home_timeline(
    request: Request,
    tasks: BackgroundTasks,
    feed: FeedService = Depends(get_feed_service(name='home')),
    db: Session = Depends(get_db_session),
) -> list[StatusItem]:
    
    feed.load_or_create()
    feed.set_sources(get_sources(request.state.session, db))
    recommendations = feed.get_recommendations(settings.feed_samples_page_size)

    items = load_status_items(recommendations, db)

    print("seen", feed.feed.seen_ids)

    return items

# @router.get('/feeds/links')
# async def timeline(
#     session: Session = Depends(get_session),
# ):
#     statuses = links_feed(session)

#     return [StatusItem.from_model(status) for status in statuses]

@router.get('/feeds/images')
async def feeds_images(
    request: Request,
    tasks: BackgroundTasks,
    feed: FeedService = Depends(get_feed_service(name='images')),
    db: Session = Depends(get_db_session),
) -> list[StatusItem]:
    
    feed.load_or_create()
    sources = get_sources(request.state.session, db)

    for source in sources:
        # if isinstance(source, DatabaseSource):
        source.with_query(lambda q: (
            q.join(MediaAttachment, Status.id == MediaAttachment.status_id)
            .where(MediaAttachment.type == 0)
            .where(MediaAttachment.aspect_ratio.between(0.7, 1.5))
        ))

    feed.set_sources(sources)
    recommendations = feed.get_recommendations(settings.feed_samples_page_size)

    items = load_status_items(recommendations, db)

    print("seen", feed.feed.seen_ids)

    return items

# @router.get('/feeds/shorts')
# async def timeline(
#     session: Session = Depends(get_session),
# ):
#     statuses = shorts_feed(session)

#     return [StatusItem.from_model(status) for status in statuses]

# @router.get('/feeds/topics/{topic}')
# async def timeline(
#     topic: str,
#     session: Session = Depends(get_session),
# ):
#     statuses = topic_feed(session, topic)

#     return [StatusItem.from_model(status) for status in statuses]

# @router.get('/topics')
# async def topics(
#     session: Session = Depends(get_session),
# ):
#     query = (
#         select(Topic, func.count(StatusTopic.topic_id))
#             .outerjoin(StatusTopic, Topic.id == StatusTopic.status_id)
#             .group_by(Topic.id)
#             .order_by(func.count(StatusTopic.topic_id).desc())
#             .limit(5)
#     )
    
#     rows = session.exec(query).all()

#     return [TopicItem.from_model(row.Topic) for row in rows]

# @router.get('/accounts/lookup', response_model=AccountItem)
# async def lookup(
#     acct: str | None = None,
#     session: Session = Depends(get_session),
# ):
#     if acct is None:
#         raise HTTPException(status_code=404)

#     if '@' in acct:
#         domain = acct.split('@')[-1]
#         username = acct.split('@')[0]

#     account = session.exec(select(Account).where(
#         func.lower(Account.domain) == domain.lower(),
#         func.lower(Account.username) == username.lower(),
#     )).first()

#     if not account:
#         raise HTTPException(status_code=404)
    
#     return AccountItem.from_model(account)

# @router.get('/accounts/{id}', response_model=AccountItem)
# async def timeline(
#     id: int,
#     session: Session = Depends(get_session),
# ):
#     account = session.get(Account, id)
    
#     return AccountItem.from_model(account)