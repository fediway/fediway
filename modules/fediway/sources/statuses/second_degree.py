import math
from datetime import UTC, datetime

from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class SecondDegreeSource(Source):
    _id = "second_degree"
    _tracked_params = ["min_mutual_follows", "max_per_author"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_mutual_follows: int = 3,
        max_per_author: int = 2,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_mutual_follows = min_mutual_follows
        self.max_per_author = max_per_author

    def _get_candidates(self, limit: int):
        query = text("""
            SELECT status_id, author_id, followed_by_count, created_at
            FROM second_degree_recent_statuses
            WHERE user_id = :user_id
              AND followed_by_count >= :min_mutual
            ORDER BY followed_by_count DESC, created_at DESC
            LIMIT :limit
        """)
        return self.rw.execute(query, {
            "user_id": self.account_id,
            "min_mutual": self.min_mutual_follows,
            "limit": limit,
        }).fetchall()

    def _score_candidates(self, candidates, max_followed_by):
        now = datetime.now(UTC).replace(tzinfo=None)
        scored = []

        for row in candidates:
            status_id, author_id, followed_by_count, created_at = row

            if max_followed_by > 0:
                social_proof = math.log(1 + followed_by_count) / math.log(1 + max_followed_by)
            else:
                social_proof = 1.0

            age_hours = (now - created_at).total_seconds() / 3600
            recency = 0.5 ** (age_hours / 12)

            score = social_proof * recency

            scored.append({
                "status_id": status_id,
                "author_id": author_id,
                "followed_by_count": followed_by_count,
                "score": score,
            })

        return scored

    def _apply_diversity(self, scored, limit):
        author_counts = {}
        result = []

        for item in sorted(scored, key=lambda x: -x["score"]):
            author = item["author_id"]
            if author_counts.get(author, 0) >= self.max_per_author:
                continue
            result.append(item)
            author_counts[author] = author_counts.get(author, 0) + 1
            if len(result) >= limit:
                break

        return result

    def collect(self, limit: int):
        candidates = self._get_candidates(limit * 5)
        if not candidates:
            return []

        max_followed_by = max(row[2] for row in candidates)

        scored = self._score_candidates(candidates, max_followed_by)
        diversified = self._apply_diversity(scored, limit)

        return [item["status_id"] for item in diversified]
