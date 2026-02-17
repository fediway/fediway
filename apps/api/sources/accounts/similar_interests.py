from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class SimilarInterestsSource(Source):
    _id = "similar_interests"
    _tracked_params = ["min_tag_overlap", "exclude_following"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_tag_overlap: int = 3,
        exclude_following: bool = True,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_tag_overlap = min_tag_overlap
        self.exclude_following = exclude_following

    def _get_followed_ids(self) -> set:
        query = text("SELECT target_account_id FROM follows WHERE account_id = :user_id")
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0] for row in result.fetchall()}

    def collect(self, limit: int):
        query = text("""
            SELECT apt.author_id, COUNT(DISTINCT apt.tag_id) AS overlap_count
            FROM user_top_tags ut
            JOIN author_primary_tags apt ON apt.tag_id = ut.tag_id
            WHERE ut.user_id = :account_id
              AND apt.author_id != :account_id
            GROUP BY apt.author_id
            HAVING COUNT(DISTINCT apt.tag_id) >= :min_overlap
            ORDER BY overlap_count DESC
            LIMIT :limit
        """)

        result = self.rw.execute(
            query,
            {
                "account_id": self.account_id,
                "min_overlap": self.min_tag_overlap,
                "limit": limit * 3,
            },
        )

        candidates = result.fetchall()

        if not self.exclude_following:
            return [row[0] for row in candidates[:limit]]

        followed_ids = self._get_followed_ids()
        return [row[0] for row in candidates if row[0] not in followed_ids][:limit]
