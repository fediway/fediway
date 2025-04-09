
from datetime import datetime
from sqlmodel import Session, func, select, exists, case
from sqlalchemy.orm import selectinload

from app.modules.models import Status, StatusTag, Mention, MediaAttachment

from .base import Feature

class NumImages(Feature):
    __featname__ = 'num_images'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 0).label("num_videos")
        )

        if MediaAttachment not in [j.right for j in q._compile_state()._join_entities]:
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(row):
        return sum([m.type == 0 for m in row.Status.media_attachments])

class NumGifs(Feature):
    __featname__ = 'num_gifs'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 1).label("num_videos")
        )

        if MediaAttachment not in [j.right for j in q._compile_state()._join_entities]:
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(row):
        return sum([m.type == 1 for m in row.Status.media_attachments])

class NumVideos(Feature):
    __featname__ = 'num_videos'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 4).label("num_videos")
        )

        if MediaAttachment not in [j.right for j in q._compile_state()._join_entities]:
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(row):
        return sum([m.type == 4 for m in row.Status.media_attachments])

class NumTags(Feature):
    __featname__ = 'num_tags'

    def query(q):
        return (
            q.add_columns(func.count(StatusTag.status_id).label("num_tags"))
            .outerjoin(StatusTag, Status.id == StatusTag.status_id)
        )

    def get(row):
        return row.num_tags

class NumMentions(Feature):
    __featname__ = 'num_mentions'

    def query(q):
        return (
            q.add_columns(func.count(Mention.status_id).label("num_mentions"))
            .outerjoin(Mention, Status.id == Mention.status_id)
        )

    def get(row):
        return row.num_mentions

class AgeInSeconds(Feature):
    __featname__ = 'age_in_seconds'

    def get(row):
        return (datetime.now() - row.Status.created_at).seconds

