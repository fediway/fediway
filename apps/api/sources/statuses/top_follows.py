import math
from datetime import datetime, timezone

from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class TopFollowsSource(Source):
    _id = "top_follows"
    _tracked_params = [
        "recency_half_life_hours",
        "max_age_hours",
        "max_per_author",
    ]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        recency_half_life_hours: float = 12,
        max_age_hours: int = 48,
        max_per_author: int = 3,
    ):
        self.rw = rw
        self.account_id = account_id
        self.recency_half_life_hours = recency_half_life_hours
        self.max_age_hours = max_age_hours
        self.max_per_author = max_per_author

    def _get_affinities(self) -> dict[int, dict]:
        query = text("""
            SELECT author_id, direct_affinity, inferred_affinity,
                   effective_affinity, affinity_source
            FROM user_followed_affinity
            WHERE user_id = :user_id
        """)
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {
            row[0]: {
                "direct_affinity": row[1],
                "inferred_affinity": row[2],
                "effective_affinity": row[3],
                "source": row[4],
            }
            for row in result.fetchall()
        }

    def _get_recent_posts(self, limit: int):
        query = text("""
            SELECT
                s.id AS status_id,
                s.account_id AS author_id,
                s.created_at
            FROM follows f
            JOIN statuses s ON s.account_id = f.target_account_id
            WHERE f.account_id = :user_id
              AND s.created_at > NOW()::TIMESTAMP - :max_age_hours * INTERVAL '1 HOUR'
              AND s.visibility IN (0, 1)
              AND s.reblog_of_id IS NULL
              AND s.deleted_at IS NULL
            ORDER BY s.created_at DESC
            LIMIT :limit
        """)
        return self.rw.execute(
            query,
            {
                "user_id": self.account_id,
                "max_age_hours": self.max_age_hours,
                "limit": limit,
            },
        ).fetchall()

    def _score_posts(self, posts, affinities, max_affinity):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        scored = []

        for row in posts:
            status_id, author_id, created_at = row
            aff = affinities.get(author_id, {})
            effective_affinity = aff.get("effective_affinity", 0)

            if max_affinity > 0:
                affinity_weight = math.log(1 + effective_affinity) / math.log(1 + max_affinity)
            else:
                affinity_weight = 1.0

            age_hours = (now - created_at).total_seconds() / 3600
            recency = 0.5 ** (age_hours / self.recency_half_life_hours)

            score = affinity_weight * recency

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
        affinities = self._get_affinities()
        max_affinity = max((a["effective_affinity"] for a in affinities.values()), default=0)

        posts = self._get_recent_posts(limit * 5)
        if not posts:
            return []

        scored = self._score_posts(posts, affinities, max_affinity)
        diversified = self._apply_diversity(scored, limit)

        return [item["status_id"] for item in diversified]
