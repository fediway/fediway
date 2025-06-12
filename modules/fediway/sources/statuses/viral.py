from sqlmodel import Session, text
from datetime import datetime, timedelta
from redis import Redis
import numpy as np

from ..base import RedisSource


class ViralSource(RedisSource):
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

    def group(self):
        return "viral"

    def name(self):
        return f"viral[l={self.language}]"

    def compute(self):
        query = f"""
        SELECT v.status_id, v.score
        FROM status_viral_scores v
        JOIN statuses s ON s.id = v.status_id AND s.language = :language
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
            len(scores), size=limit, p=probabilities, replace=False
        )

        return np.array(status_ids)[sampled_indices].tolist()
