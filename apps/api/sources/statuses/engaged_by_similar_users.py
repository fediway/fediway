from datetime import datetime, timezone

from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class EngagedBySimilarUsersSource(Source):
    _id = "engaged_by_similar_users"
    _tracked_params = ["min_similarity", "max_per_author"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_similarity: float = 0.05,
        max_per_author: int = 2,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_similarity = min_similarity
        self.max_per_author = max_per_author

    def _get_candidates(self, limit: int):
        query = text("""
            SELECT status_id, author_id, similarity, engagement_weight, event_time
            FROM similar_user_recent_engagements
            WHERE user_id = :user_id
              AND similarity >= :min_similarity
            LIMIT :limit
        """)
        return self.rw.execute(
            query,
            {
                "user_id": self.account_id,
                "min_similarity": self.min_similarity,
                "limit": limit,
            },
        ).fetchall()

    def _get_followed_ids(self) -> set:
        query = text("SELECT target_account_id FROM follows WHERE account_id = :user_id")
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0] for row in result.fetchall()}

    def _aggregate_scores(self, candidates):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        status_data = {}

        for row in candidates:
            status_id, author_id, similarity, engagement_weight, event_time = row

            if status_id not in status_data:
                status_data[status_id] = {
                    "status_id": status_id,
                    "author_id": author_id,
                    "score": 0,
                    "engagement_count": 0,
                }

            age_hours = (now - event_time).total_seconds() / 3600
            recency = 0.5 ** (age_hours / 12)
            status_data[status_id]["score"] += similarity * engagement_weight * recency
            status_data[status_id]["engagement_count"] += 1

        return sorted(status_data.values(), key=lambda x: -x["score"])

    def _apply_diversity(self, scored, limit):
        author_counts = {}
        result = []

        for item in scored:
            author = item["author_id"]
            if author_counts.get(author, 0) >= self.max_per_author:
                continue
            result.append(item)
            author_counts[author] = author_counts.get(author, 0) + 1
            if len(result) >= limit:
                break

        return result

    def collect(self, limit: int):
        candidates = self._get_candidates(limit * 10)
        if not candidates:
            return []

        aggregated = self._aggregate_scores(candidates)

        followed_ids = self._get_followed_ids()
        out_network = [s for s in aggregated if s["author_id"] not in followed_ids]

        diversified = self._apply_diversity(out_network, limit)

        return [item["status_id"] for item in diversified]


class PopularPostsSource(Source):
    _id = "popular_posts"
    _tracked_params = ["max_per_author"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        max_per_author: int = 2,
    ):
        self.rw = rw
        self.account_id = account_id
        self.max_per_author = max_per_author

    def _get_followed_ids(self) -> set:
        query = text("SELECT target_account_id FROM follows WHERE account_id = :user_id")
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0] for row in result.fetchall()}

    def _get_popular_with_active_users(self, limit: int):
        query = text("""
            SELECT status_id, author_id, engager_count, weighted_engagement
            FROM popular_posts
            ORDER BY weighted_engagement DESC
            LIMIT :limit
        """)
        return self.rw.execute(query, {"limit": limit}).fetchall()

    def _apply_diversity(self, candidates, followed_ids, limit):
        author_counts = {}
        result = []

        for row in candidates:
            status_id, author_id, engager_count, weighted_engagement = row

            if author_id in followed_ids:
                continue

            if author_counts.get(author_id, 0) >= self.max_per_author:
                continue

            result.append({"status_id": status_id, "author_id": author_id})
            author_counts[author_id] = author_counts.get(author_id, 0) + 1

            if len(result) >= limit:
                break

        return result

    def collect(self, limit: int):
        followed_ids = self._get_followed_ids()
        candidates = self._get_popular_with_active_users(limit * 5)

        if not candidates:
            return []

        diversified = self._apply_diversity(candidates, followed_ids, limit)

        return [item["status_id"] for item in diversified]
