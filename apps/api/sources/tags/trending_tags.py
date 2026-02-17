import math
from datetime import timedelta

import numpy as np
from redis import Redis
from sqlmodel import Session, text

from modules.fediway.sources.base import RedisSource


class TrendingTagsSource(RedisSource):
    _id = "trending_tags"
    _tracked_params = ["language", "min_posts", "min_accounts"]

    def __init__(
        self,
        r: Redis,
        rw: Session | None = None,
        language: str = "en",
        min_posts: int = 3,
        min_accounts: int = 2,
        blocked_tags: list[str] | None = None,
        ttl: timedelta = timedelta(minutes=10),
    ):
        super().__init__(r=r, ttl=ttl)
        self.rw = rw
        self.language = language
        self.min_posts = min_posts
        self.min_accounts = min_accounts
        self.blocked_tags = blocked_tags or []

    def redis_key(self):
        return f"source:{self.id}:{self.language}"

    def compute(self):
        blocked_clause = ""
        if self.blocked_tags:
            placeholders = ", ".join([f":blocked_{i}" for i in range(len(self.blocked_tags))])
            blocked_clause = f"AND t.name NOT IN ({placeholders})"

        query = f"""
        SELECT
            ts.tag_id,
            t.name,
            ts.post_count,
            ts.account_count,
            COALESCE(tsr.post_count, 0) AS recent_post_count,
            COALESCE(tsr.account_count, 0) AS recent_account_count
        FROM trending_tag_stats ts
        JOIN tags t ON t.id = ts.tag_id
        LEFT JOIN trending_tag_stats_recent tsr
            ON tsr.tag_id = ts.tag_id AND tsr.language = ts.language
        WHERE ts.language = :language
          AND t.trendable IS NOT FALSE
          AND t.listable IS NOT FALSE
          AND ts.post_count >= :min_posts
          AND ts.account_count >= :min_accounts
          {blocked_clause}
        ORDER BY COALESCE(tsr.account_count, 0) DESC
        LIMIT 200;
        """

        params = {
            "language": self.language,
            "min_posts": self.min_posts,
            "min_accounts": self.min_accounts,
        }

        for i, tag in enumerate(self.blocked_tags):
            params[f"blocked_{i}"] = tag

        for row in self.rw.execute(text(query), params).fetchall():
            tag_id, name, post_count, account_count, recent_posts, recent_accounts = row

            # Velocity: what fraction of activity happened in the last 6h?
            # High ratio = accelerating tag, low ratio = steady/declining
            velocity = recent_posts / (post_count - recent_posts + 1)

            # Breadth: unique accounts prevent single-user spam
            breadth = math.log(1 + account_count)

            # Recent breadth bonus: many different people posting recently
            recent_breadth = math.log(1 + recent_accounts)

            score = velocity * breadth * (1 + recent_breadth)

            yield {
                "tag_id": tag_id,
                "name": name,
                "post_count": post_count,
                "account_count": account_count,
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
