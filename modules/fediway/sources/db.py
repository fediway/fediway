
from sqlmodel import Session, select, func, desc
from datetime import datetime, timedelta

from modules.mastodon.models import Status, StatusStats
from .base import Source

class DatabaseSource(Source):
    def __init__(self, db: Session, query_callbacks: list[callable] = []):
        self.db = db
        self.query_callbacks = query_callbacks

    def with_query(self, callback):
        self.query_callbacks.append(callback)

    def base_query(self, limit: int):
        raise NotImplemented

    def query(self, limit: int):
        query = self.base_query(limit)

        for cb in self.query_callbacks:
            query = cb(query)

        return query

    def collect(self, max_n: int):
        for candidate in self.db.exec(self.query(max_n)).all():
            yield candidate

class HotStatuses(DatabaseSource):
    def __init__(self, 
                 decay_lambda: float = 2.0, 
                 max_age: timedelta = timedelta(days=7), 
                 *pargs, **kwargs):
        super().__init__(*pargs, **kwargs)

        self.decay_lambda = decay_lambda
        self.max_age = max_age

    def priority_query(self):
        # Calculate age in days using PostgreSQL's NOW()
        age_in_days = func.extract('epoch', func.now() - Status.created_at) / 86400

        favourites_count = func.coalesce(StatusStats.favourites_count, 0)
        reblogs_count = func.coalesce(StatusStats.reblogs_count, 0)
        replies_count = func.coalesce(StatusStats.replies_count, 0)

        # Weight calculation formula
        weight = (
            (favourites_count + 1) * 0.5 +
            (reblogs_count + 1) * 2 +
            (replies_count + 1) * 5 +
            func.exp(-self.decay_lambda * age_in_days) * 100
        )

        # Priority calculation using exponential distribution trick
        priority = -func.ln(1.0 - func.random()) / weight

        return priority

    def base_query(self, limit: int):
        priority = self.priority_query()

        return (
            select(Status.id)
            .join(StatusStats, Status.id == StatusStats.status_id)
            .where(Status.created_at > datetime.now() - self.max_age)
            .order_by(priority)
            .limit(limit)
        )

    def __str__(self):
        return f'hot_statuses'

class HotStatusesByLanguage(HotStatuses):
    def __init__(self, 
                 language: str = 'en',
                 *pargs, **kwargs):
        super().__init__(*pargs, **kwargs)

        self.language = language

    def base_query(self, limit: int):
        return super().base_query(limit).where(Status.language == self.language)

    def __str__(self):
        return f'hot_statuses_in_a_language[{self.language}]'

class NewStatuses(DatabaseSource):
    def base_query(self, limit: int):
        return (
            select(Status.id)
            .order_by(desc(Status.created_at))
            .limit(limit)
        )

class NewStatusesByLanguage(NewStatuses):
    def __init__(self, 
                 language: str | list = 'en',
                 *pargs, **kwargs):
        super().__init__(*pargs, **kwargs)

        self.language = language

    def base_query(self, limit: int):
        q = super().base_query(limit)
        
        if type(self.language) is list:
            return q.where(Status.language._in( self.language))
        else:
            return q.where(Status.language == self.language)