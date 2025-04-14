
from datetime import datetime
from sqlmodel import Session, func, select, exists, case
from sqlalchemy.orm import selectinload

from app.modules.models import Status, StatusStats, StatusTag, Mention, MediaAttachment

from .base import Feature
from .utils import is_joined

class NumImages(Feature):
    __featname__ = 'num_images'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 0).label("num_images")
        )

        if not is_joined(q, MediaAttachment):
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(num_images, **kwargs):
        return num_images

class NumGifs(Feature):
    __featname__ = 'num_gifs'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 1).label("num_gifs")
        )

        if not is_joined(q, MediaAttachment):
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(num_gifs, **kwargs):
        return num_gifs

class NumVideos(Feature):
    __featname__ = 'num_videos'

    def query(q):
        q = q.add_columns(
            func.count().filter(MediaAttachment.type == 4).label("num_videos")
        )

        if not is_joined(q, MediaAttachment):
            q = q.outerjoin(MediaAttachment, Status.id == MediaAttachment.status_id)

        return q

    def get(num_videos, **kwargs):
        return num_videos

class NumTags(Feature):
    __featname__ = 'num_tags'

    def query(q):
        return (
            q.add_columns(func.count(StatusTag.status_id).label("num_tags"))
            .outerjoin(StatusTag, Status.id == StatusTag.status_id)
        )

    def get(num_tags, **kwargs):
        return num_tags

class NumMentions(Feature):
    __featname__ = 'num_mentions'

    def query(q):
        return (
            q.add_columns(func.count(Mention.status_id).label("num_mentions"))
            .outerjoin(Mention, Status.id == Mention.status_id)
        )

    def get(num_mentions, **kwargs):
        return num_mentions

class NumFavourites(Feature):
    __featname__ = 'num_favourites'

    def query(q):
        q = q.add_columns(func.max(StatusStats.favourites_count).label("num_favourites"))

        if not is_joined(q, StatusStats):
            q = q.join(StatusStats, Status.id == StatusStats.status_id)

        return q

    def get(num_favourites, **kwargs):
        return num_favourites

class NumReblogs(Feature):
    __featname__ = 'num_reblogs'

    def query(q):
        q = q.add_columns(func.max(StatusStats.reblogs_count).label("num_reblogs"))

        if not is_joined(q, StatusStats):
            q = q.join(StatusStats, Status.id == StatusStats.status_id)

        return q

    def get(num_reblogs, **kwargs):
        return num_reblogs

class NumReplies(Feature):
    __featname__ = 'num_replies'

    def query(q):
        q = q.add_columns(func.max(StatusStats.favourites_count).label("num_replies"))

        if not is_joined(q, StatusStats):
            q = q.join(StatusStats, Status.id == StatusStats.status_id)

        return q

    def get(num_replies, **kwargs):
        return num_replies

class AgeInSeconds(Feature):
    __featname__ = 'age_in_seconds'

    def query(q):
        return q.add_columns(Status.created_at)

    def get(created_at, **kwargs):
        return (datetime.now() - created_at).seconds