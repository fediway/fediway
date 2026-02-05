from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class PopularAccountsSource(Source):
    _id = "popular_accounts"
    _tracked_params = ["min_followers", "local_only", "exclude_following", "min_account_age_days"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_followers: int = 10,
        local_only: bool = True,
        exclude_following: bool = True,
        min_account_age_days: int = 7,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_followers = min_followers
        self.local_only = local_only
        self.exclude_following = exclude_following
        self.min_account_age_days = min_account_age_days

    def collect(self, limit: int):
        query = text("""
            SELECT
                a.id AS account_id,
                COUNT(f.id) AS follower_count
            FROM accounts a
            JOIN follows f ON f.target_account_id = a.id
            LEFT JOIN follows existing
                ON existing.account_id = :account_id
                AND existing.target_account_id = a.id
            WHERE a.id != :account_id
              AND a.suspended_at IS NULL
              AND a.silenced_at IS NULL
              AND (:local_only = false OR a.domain IS NULL)
              AND a.created_at < NOW() - INTERVAL :min_age_days DAY
              AND (:exclude_following = false OR existing.id IS NULL)
            GROUP BY a.id
            HAVING COUNT(f.id) >= :min_followers
            ORDER BY COUNT(f.id) DESC
            LIMIT :limit
        """)

        result = self.rw.execute(
            query,
            {
                "account_id": self.account_id,
                "min_followers": self.min_followers,
                "local_only": self.local_only,
                "exclude_following": self.exclude_following,
                "min_age_days": self.min_account_age_days,
                "limit": limit,
            },
        )

        return [row[0] for row in result.fetchall()]
