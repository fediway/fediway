from datetime import timedelta

import numpy as np
from redis import Redis
from sqlmodel import Session, text

from modules.fediway.sources.base import RedisSource


class TrendingTagsSource(RedisSource):
    _id = "trending_tags"
    _tracked_params = ["window_hours", "min_posts", "min_accounts", "local_only"]

    def __init__(
        self,
        r: Redis,
        rw: Session | None = None,
        window_hours: int = 24,
        min_posts: int = 3,
        min_accounts: int = 2,
        local_only: bool = False,
        weight_posts: float = 1.0,
        weight_accounts: float = 2.0,
        velocity_boost: bool = True,
        blocked_tags: list[str] | None = None,
        ttl: timedelta = timedelta(minutes=10),
    ):
        super().__init__(r=r, ttl=ttl)
        self.rw = rw
        self.window_hours = window_hours
        self.min_posts = min_posts
        self.min_accounts = min_accounts
        self.local_only = local_only
        self.weight_posts = weight_posts
        self.weight_accounts = weight_accounts
        self.velocity_boost = velocity_boost
        self.blocked_tags = blocked_tags or []

    def redis_key(self):
        local_suffix = "_local" if self.local_only else ""
        return f"source:{self.id}:{self.window_hours}h{local_suffix}"

    def compute(self):
        blocked_clause = ""
        if self.blocked_tags:
            placeholders = ", ".join([f":blocked_{i}" for i in range(len(self.blocked_tags))])
            blocked_clause = f"AND t.name NOT IN ({placeholders})"

        local_clause = ""
        if self.local_only:
            local_clause = "AND a.domain IS NULL"

        query = f"""
        WITH tag_stats AS (
            SELECT
                st.tag_id,
                COUNT(DISTINCT st.status_id) as post_count,
                COUNT(DISTINCT s.account_id) as account_count,
                MAX(s.created_at) as last_used
            FROM statuses_tags st
            JOIN statuses s ON s.id = st.status_id
            JOIN accounts a ON a.id = s.account_id
            WHERE s.created_at > NOW() - INTERVAL ':window_hours hours'
              AND s.deleted_at IS NULL
              AND s.visibility IN (0, 1)
              {local_clause}
            GROUP BY st.tag_id
            HAVING COUNT(DISTINCT st.status_id) >= :min_posts
               AND COUNT(DISTINCT s.account_id) >= :min_accounts
        )
        SELECT
            ts.tag_id,
            t.name,
            ts.post_count,
            ts.account_count,
            ts.last_used
        FROM tag_stats ts
        JOIN tags t ON t.id = ts.tag_id
        WHERE t.trendable = true
          AND t.listable = true
          {blocked_clause}
        ORDER BY ts.account_count DESC, ts.post_count DESC
        LIMIT 200;
        """

        params = {
            "window_hours": self.window_hours,
            "min_posts": self.min_posts,
            "min_accounts": self.min_accounts,
        }

        for i, tag in enumerate(self.blocked_tags):
            params[f"blocked_{i}"] = tag

        for row in self.rw.execute(text(query), params).fetchall():
            score = row[2] * self.weight_posts + row[3] * self.weight_accounts

            if self.velocity_boost:
                # Boost recently active tags
                hours_since_last = 1  # simplified - would calculate from last_used
                score *= 1 + (1 / (hours_since_last + 1))

            yield {
                "tag_id": row[0],
                "name": row[1],
                "post_count": row[2],
                "account_count": row[3],
                "score": score,
            }

    def collect(self, limit: int):
        candidates = self.load()
        if not candidates:
            return

        scores = np.array([c["score"] for c in candidates])
        if scores.sum() == 0:
            for c in candidates[:limit]:
                yield c["tag_id"]
            return

        probabilities = scores / scores.sum()
        sample_size = min(limit, len(candidates))

        sampled_indices = np.random.choice(
            len(candidates),
            size=sample_size,
            p=probabilities,
            replace=False,
        )

        for i in sampled_indices:
            yield candidates[i]["tag_id"]
