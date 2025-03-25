
import math
from sqlmodel import Session, select, func
from sqlalchemy.engine.row import Row
from datetime import datetime, timedelta

from .candidate import Candidate
from .base import Feed

from app.modules.models.status import Status, StatusStats
from app.modules.models.account import Account, AccountStats
from app.modules.models.media_attachment import MediaAttachment
from app.modules.models.preview_card import PreviewCard, PreviewCardStatus
from app.modules.models.topic import Topic, StatusTopic

from app.utils import sql_string

def home_feed(session: Session, max_age_days: int = 3, limit: int = 10) -> list[Row]:
    priority = get_priority_query()

    query = (
        select(Status, StatusStats)
        .where(Status.id == StatusStats.status_id)
        .where(Status.created_at > datetime.now() - timedelta(days=max_age_days))
        .order_by(priority)
        .limit(limit)
    )

    rows = session.exec(query).all()
    rows = merge_relationships(rows, session)

    return rows

def links_feed(session: Session, max_age_days: int = 3, limit: int = 10) -> list[Row]:
    priority = get_priority_query()

    query = (
        select(Status, StatusStats)
        .join(PreviewCardStatus, Status.id == PreviewCardStatus.status_id)
        .join(PreviewCard, PreviewCard.id == PreviewCardStatus.preview_card_id)
        .where(Status.id == StatusStats.status_id)
        .where(Status.created_at > datetime.now() - timedelta(days=max_age_days))
        .order_by(priority)
        .limit(limit)
    )

    rows = session.exec(query).all()
    rows = merge_relationships(rows, session)

    return rows

def image_feed(session: Session, max_age_days: int = 3, limit: int = 10) -> list[Row]:
    priority = get_priority_query()
    
    query = (
        select(Status, StatusStats)
        .join(MediaAttachment, Status.id == MediaAttachment.status_id)
        .where(Status.id == StatusStats.status_id)
        .where(MediaAttachment.type == 0)
        .where(MediaAttachment.aspect_ratio.between(0.7, 1.5))
        .where(Status.created_at > datetime.now() - timedelta(days=max_age_days))
        .order_by(priority)
        .limit(limit)
    )

    rows = session.exec(query).all()
    rows = merge_relationships(rows, session)

    return rows

def shorts_feed(session: Session, max_age_days: int = 3, limit: int = 10) -> list[Row]:
    priority = get_priority_query()
    
    query = (
        select(Status, StatusStats)
        .join(MediaAttachment, Status.id == MediaAttachment.status_id)
        .where(Status.id == StatusStats.status_id)
        .where(MediaAttachment.type == 4)
        # .where(MediaAttachment.aspect_ratio.between(1.0, 2.5))
        .where(Status.created_at > datetime.now() - timedelta(days=max_age_days))
        .order_by(priority)
        .limit(limit)
    )

    rows = session.exec(query).all()
    rows = merge_relationships(rows, session)

    return rows

def topic_feed(session: Session, topic: str, max_age_days: int = 3, limit: int = 10) -> list[Row]:
    priority = get_priority_query()

    topic_id = session.scalar(select(Topic.id).filter_by(name=topic))

    query = (
        select(Status, StatusStats)
        .join(StatusTopic, Status.id == StatusTopic.status_id)
        .where(StatusTopic.topic_id == topic_id)
        .where(Status.id == StatusStats.status_id)
        .where(Status.created_at > datetime.now() - timedelta(days=max_age_days))
        .order_by(priority)
        .limit(limit)
    )

    print(sql_string(query))

    rows = session.exec(query).all()
    rows = merge_relationships(rows, session)

    return rows

def merge_relationships(rows: list[Row], session: Session) -> list[Status]:
    # load accounts
    account_ids = {row.Status.account_id for row in rows}
    accounts = session.exec(
        select(Account, AccountStats)
        .where(Account.id.in_(account_ids))
        .where(Account.id == AccountStats.account_id)
    ).all()
    account_map = {row.Account.id: row for row in accounts}

    # load media_attachments
    if not 'MediaAttachment' in rows[0]:
        status_ids = {row.Status.id for row in rows}
        media_attachments = session.exec(
            select(MediaAttachment)
            .where(MediaAttachment.status_id.in_(status_ids))
        ).all()
        media_attachments_map = {status_id: [] for status_id in status_ids}
        for media_attachment in media_attachments:
            media_attachments_map[media_attachment.status_id].append(media_attachment)
    
    statuses = []

    # attach relationships to status
    for row in rows:
        status = row.Status
        status.stats = row.StatusStats
        status.account = account_map[status.account_id].Account
        status.account.stats = account_map[status.account_id].AccountStats
        if 'MediaAttachment' in status:
            status.media_attachments = row.MediaAttachment
        else:
            status.media_attachments = media_attachments_map[status.id]
        status.media_attachments = [m for m in status.media_attachments if m.id in status.ordered_media_attachment_ids]
        statuses.append(status)
    
    return statuses

def get_priority_query(decay_lambda: float = 2.0):
    # Calculate age in days using PostgreSQL's NOW()
    age_days = func.extract('epoch', func.now() - Status.created_at) / 86400

    favourites_count = func.coalesce(StatusStats.favourites_count, 0)
    reblogs_count = func.coalesce(StatusStats.reblogs_count, 0)

    # Weight calculation formula
    weight = (
        (favourites_count + 1) *
        # (reblogs_count + 1) *
        func.exp(-decay_lambda * age_days)
    )

    # Priority calculation using exponential distribution trick
    priority = -func.ln(1.0 - func.random()) / weight

    return priority