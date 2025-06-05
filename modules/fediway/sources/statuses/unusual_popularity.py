from sqlmodel import Session, text
from datetime import datetime, timedelta
from redis import Redis
from neo4j import Driver

from ..base import RedisSource


class UnusualPopularitySource(RedisSource):
    def __init__(
        self,
        r: Redis,
        rw: Session | None = None,
        language: str = "en",
        top_n: int = 5000,
        decay_rate: float = 1.0,
        max_age_in_days: int = 3,
        ttl: timedelta = timedelta(minutes=10),
    ):
        super().__init__(r=r, ttl=ttl)

        self.rw = rw
        self.language = language
        self.top_n = top_n
        self.decay_rate = decay_rate
        self.max_age_in_days = max_age_in_days

    def group(self):
        return "unusual_popularity"

    def name(self):
        return f"unusual_popularity[l={self.language},d={self.decay_rate}]"

    def compute(self):
        query = f"""
        SELECT *
        FROM (
            SELECT
                sc.status_id,
                (
                    sc.unusual_popularity_score * 
                    exp(-{self.decay_rate} * EXTRACT(EPOCH FROM (NOW() - s.created_at)) / (3600 * 24))
                ) as score
            FROM status_scores sc
            JOIN statuses s on s.id = sc.status_id and s.language = '{self.language}' and s.created_at > NOW() - interval '{self.max_age_in_days} DAYS'
        ) s
        ORDER BY s.score DESC
        LIMIT {self.top_n};
        """

        for result in self.rw.exec(text(query)).fetchall():
            yield result[0]
