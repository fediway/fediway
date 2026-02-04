import math
from datetime import UTC, datetime

from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class TagAffinitySource(Source):
    _id = "tag_affinity"
    _tracked_params = ["max_age_hours", "max_per_tag", "max_per_author", "in_network_penalty"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        max_age_hours: int = 48,
        max_per_tag: int = 5,
        max_per_author: int = 2,
        in_network_penalty: float = 0.5,
    ):
        self.rw = rw
        self.account_id = account_id
        self.max_age_hours = max_age_hours
        self.max_per_tag = max_per_tag
        self.max_per_author = max_per_author
        self.in_network_penalty = in_network_penalty

    def _get_tag_affinities(self) -> dict[int, float]:
        query = text("""
            SELECT tag_id, raw_affinity
            FROM user_top_tags
            WHERE user_id = :user_id
        """)
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0]: row[1] for row in result.fetchall()}

    def _get_inferred_tag_affinities(self) -> dict[int, float]:
        query = text("""
            SELECT tag_id, avg_usage * contributing_accounts AS inferred_affinity
            FROM user_inferred_tag_affinity
            WHERE user_id = :user_id
        """)
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0]: row[1] * 0.7 for row in result.fetchall()}

    def _get_followed_ids(self) -> set:
        query = text("SELECT target_account_id FROM follows WHERE account_id = :user_id")
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0] for row in result.fetchall()}

    def _get_tag_candidates(self, tag_ids: list[int], limit: int):
        if not tag_ids:
            return []
        query = text("""
            SELECT tag_id, status_id, author_id, created_at
            FROM tag_recent_statuses
            WHERE tag_id = ANY(:tag_ids)
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        return self.rw.execute(query, {
            "tag_ids": tag_ids,
            "limit": limit,
        }).fetchall()

    def _score_candidates(self, candidates, tag_affinities, max_affinity, followed_ids):
        now = datetime.now(UTC).replace(tzinfo=None)
        scored = []

        for row in candidates:
            tag_id, status_id, author_id, created_at = row
            tag_affinity = tag_affinities.get(tag_id, 0)

            if max_affinity > 0:
                affinity_weight = math.log(1 + tag_affinity) / math.log(1 + max_affinity)
            else:
                affinity_weight = 1.0

            age_hours = (now - created_at).total_seconds() / 3600
            recency = 0.5 ** (age_hours / 12)

            penalty = self.in_network_penalty if author_id in followed_ids else 0
            score = affinity_weight * recency * (1 - penalty)

            scored.append({
                "status_id": status_id,
                "author_id": author_id,
                "tag_id": tag_id,
                "score": score,
            })

        return scored

    def _apply_diversity(self, scored, limit):
        tag_counts = {}
        author_counts = {}
        result = []

        for item in sorted(scored, key=lambda x: -x["score"]):
            tag = item["tag_id"]
            author = item["author_id"]

            if tag_counts.get(tag, 0) >= self.max_per_tag:
                continue
            if author_counts.get(author, 0) >= self.max_per_author:
                continue

            result.append(item)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            author_counts[author] = author_counts.get(author, 0) + 1

            if len(result) >= limit:
                break

        return result

    def collect(self, limit: int):
        direct_affinities = self._get_tag_affinities()
        inferred_affinities = self._get_inferred_tag_affinities()

        # Blend: direct takes precedence, then inferred
        tag_affinities = {**inferred_affinities, **direct_affinities}

        if not tag_affinities:
            return []

        max_affinity = max(tag_affinities.values())
        followed_ids = self._get_followed_ids()

        candidates = self._get_tag_candidates(list(tag_affinities.keys()), limit * 10)
        if not candidates:
            return []

        scored = self._score_candidates(candidates, tag_affinities, max_affinity, followed_ids)
        diversified = self._apply_diversity(scored, limit)

        return [item["status_id"] for item in diversified]
