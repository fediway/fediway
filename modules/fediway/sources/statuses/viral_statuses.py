from datetime import timedelta

import numpy as np
from redis import Redis
from sqlmodel import Session, text

from ..base import RedisSource


class ViralStatusesSource(RedisSource):
    """Trending posts with high engagement velocity."""

    _id = "viral"
    _tracked_params = ["language", "top_n"]

    def __init__(
        self,
        r: Redis,
        rw: Session | None = None,
        language: str = "en",
        top_n: int = 100,
        ttl: timedelta = timedelta(minutes=10),
    ):
        super().__init__(r=r, ttl=ttl)

        self.rw = rw
        self.language = language
        self.top_n = top_n

    def redis_key(self):
        return f"source:{self.id}:{self.language}"

    def compute(self):
        query = """
        SELECT v.status_id, v.score
        FROM status_virality_score_languages v
        WHERE v.language = :language
        ORDER BY v.score DESC
        LIMIT :limit;
        """

        params = {
            "language": self.language,
            "limit": self.top_n,
        }

        for result in self.rw.execute(text(query), params).fetchall():
            yield {"status_id": result[0], "score": float(result[1])}

    def collect(self, limit):
        candidates = self.load()

        status_ids = [c["status_id"] for c in candidates]
        scores = np.array([c["score"] for c in candidates])

        if sum(scores) == 0:
            status_ids[:limit]

        probabilities = scores / scores.sum()

        sampled_indices = np.random.choice(
            len(scores),
            size=min(limit, len(status_ids)),
            p=probabilities,
            replace=False,
        )

        for i in sampled_indices:
            yield status_ids[i]
