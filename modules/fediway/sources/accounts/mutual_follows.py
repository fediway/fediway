from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class MutualFollowsSource(Source):
    _id = "mutual_follows"
    _tracked_params = ["min_mutual_follows", "exclude_following"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_mutual_follows: int = 2,
        exclude_following: bool = True,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_mutual_follows = min_mutual_follows
        self.exclude_following = exclude_following

    def collect(self, limit: int):
        query = text("""
            WITH my_follows AS (
                SELECT target_account_id
                FROM follows
                WHERE account_id = :account_id
            ),
            candidates AS (
                SELECT
                    f2.target_account_id AS suggested_id,
                    COUNT(*) AS mutual_count
                FROM follows f2
                JOIN my_follows mf ON f2.account_id = mf.target_account_id
                WHERE f2.target_account_id != :account_id
                GROUP BY f2.target_account_id
                HAVING COUNT(*) >= :min_mutual
            )
            SELECT c.suggested_id, c.mutual_count
            FROM candidates c
            LEFT JOIN follows existing
                ON existing.account_id = :account_id
                AND existing.target_account_id = c.suggested_id
            WHERE (:exclude_following = false OR existing.id IS NULL)
            ORDER BY c.mutual_count DESC
            LIMIT :limit
        """)

        result = self.rw.execute(
            query,
            {
                "account_id": self.account_id,
                "min_mutual": self.min_mutual_follows,
                "exclude_following": self.exclude_following,
                "limit": limit,
            },
        )

        return [row[0] for row in result.fetchall()]
