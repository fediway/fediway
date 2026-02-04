import math
from datetime import datetime, timezone

from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class FollowsEngagingNowSource(Source):
    _id = "follows_engaging_now"
    _tracked_params = ["min_engaged_follows", "max_per_author"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_engaged_follows: int = 1,
        max_per_author: int = 2,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_engaged_follows = min_engaged_follows
        self.max_per_author = max_per_author

    def _get_candidates(self, limit: int):
        query = text("""
            SELECT
                status_id,
                author_id,
                engaged_follows_count,
                latest_engagement_time,
                total_engagement_weight
            FROM follows_engaging_candidates
            WHERE user_id = :user_id
              AND engaged_follows_count >= :min_follows
            ORDER BY engaged_follows_count DESC, latest_engagement_time DESC
            LIMIT :limit
        """)
        return self.rw.execute(
            query,
            {
                "user_id": self.account_id,
                "min_follows": self.min_engaged_follows,
                "limit": limit * 5,
            },
        ).fetchall()

    def _score_candidates(self, candidates):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        scored = []

        for row in candidates:
            status_id, author_id, engaged_count, latest_time, engagement_weight = row

            social_proof = engaged_count**1.5

            engagement_age_hours = (now - latest_time).total_seconds() / 3600
            recency_boost = 0.5 ** (engagement_age_hours / 2)

            type_weight = math.log(1 + engagement_weight)

            score = social_proof * recency_boost * type_weight

            scored.append(
                {
                    "status_id": status_id,
                    "author_id": author_id,
                    "score": score,
                }
            )

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
        candidates = self._get_candidates(limit)
        if not candidates:
            return []

        scored = self._score_candidates(candidates)
        diversified = self._apply_diversity(scored, limit)

        return [item["status_id"] for item in diversified]
