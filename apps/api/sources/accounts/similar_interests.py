from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class SimilarInterestsSource(Source):
    _id = "similar_interests"
    _tracked_params = ["min_tag_overlap", "exclude_following", "lookback_days"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_tag_overlap: int = 3,
        exclude_following: bool = True,
        lookback_days: int = 30,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_tag_overlap = min_tag_overlap
        self.exclude_following = exclude_following
        self.lookback_days = lookback_days

    def collect(self, limit: int):
        query = text("""
            WITH my_tags AS (
                SELECT DISTINCT st.tag_id
                FROM statuses s
                JOIN statuses_tags st ON st.status_id = s.id
                WHERE s.account_id = :account_id
                  AND s.created_at > NOW() - INTERVAL :lookback_days DAY
            ),
            candidates AS (
                SELECT
                    s.account_id AS suggested_id,
                    COUNT(DISTINCT st.tag_id) AS overlap_count
                FROM statuses s
                JOIN statuses_tags st ON st.status_id = s.id
                JOIN my_tags mt ON mt.tag_id = st.tag_id
                WHERE s.account_id != :account_id
                  AND s.created_at > NOW() - INTERVAL :lookback_days DAY
                GROUP BY s.account_id
                HAVING COUNT(DISTINCT st.tag_id) >= :min_overlap
            )
            SELECT c.suggested_id, c.overlap_count
            FROM candidates c
            LEFT JOIN follows existing
                ON existing.account_id = :account_id
                AND existing.target_account_id = c.suggested_id
            WHERE (:exclude_following = false OR existing.id IS NULL)
            ORDER BY c.overlap_count DESC
            LIMIT :limit
        """)

        result = self.rw.execute(
            query,
            {
                "account_id": self.account_id,
                "min_overlap": self.min_tag_overlap,
                "exclude_following": self.exclude_following,
                "lookback_days": self.lookback_days,
                "limit": limit,
            },
        )

        return [row[0] for row in result.fetchall()]
