from datetime import timedelta

import numpy as np
from redis import Redis
from sqlmodel import Session, text

from modules.fediway.sources.base import RedisSource


class ViralStatusesSource(RedisSource):
    _id = "viral"
    _tracked_params = ["language", "top_n", "max_per_author"]

    def __init__(
        self,
        r: Redis,
        rw: Session | None = None,
        language: str = "en",
        top_n: int = 100,
        max_per_author: int = 2,
        ttl: timedelta = timedelta(minutes=10),
    ):
        super().__init__(r=r, ttl=ttl)
        self.rw = rw
        self.language = language
        self.top_n = top_n
        self.max_per_author = max_per_author

    def redis_key(self):
        return f"source:{self.id}:{self.language}"

    def compute(self):
        query = """
        SELECT status_id, author_id, score
        FROM status_virality_score_languages
        WHERE language = :language
        ORDER BY score DESC
        LIMIT :limit;
        """
        params = {"language": self.language, "limit": self.top_n}

        for row in self.rw.execute(text(query), params).fetchall():
            yield {
                "status_id": row[0],
                "author_id": row[1],
                "score": float(row[2]),
            }

    def _apply_diversity(self, candidates, limit):
        author_counts = {}
        result = []

        for c in sorted(candidates, key=lambda x: -x["score"]):
            author = c["author_id"]
            if author_counts.get(author, 0) >= self.max_per_author:
                continue
            result.append(c)
            author_counts[author] = author_counts.get(author, 0) + 1
            if len(result) >= limit:
                break

        return result

    def collect(self, limit):
        candidates = self.load()
        if not candidates:
            return

        diversified = self._apply_diversity(candidates, limit * 3)
        if not diversified:
            return

        scores = np.array([c["score"] for c in diversified])
        if scores.sum() == 0:
            for c in diversified[:limit]:
                yield c["status_id"]
            return

        probabilities = scores / scores.sum()
        sample_size = min(limit, len(diversified))

        sampled_indices = np.random.choice(
            len(diversified),
            size=sample_size,
            p=probabilities,
            replace=False,
        )

        for i in sampled_indices:
            yield diversified[i]["status_id"]
