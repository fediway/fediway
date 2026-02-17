from sqlmodel import Session, text

from modules.fediway.sources.base import Source


class PopularAccountsSource(Source):
    _id = "popular_accounts"
    _tracked_params = ["min_followers", "local_only", "exclude_following"]

    def __init__(
        self,
        rw: Session,
        account_id: int,
        min_followers: int = 10,
        local_only: bool = True,
        exclude_following: bool = True,
    ):
        self.rw = rw
        self.account_id = account_id
        self.min_followers = min_followers
        self.local_only = local_only
        self.exclude_following = exclude_following

    def _get_followed_ids(self) -> set:
        query = text("SELECT target_account_id FROM follows WHERE account_id = :user_id")
        result = self.rw.execute(query, {"user_id": self.account_id})
        return {row[0] for row in result.fetchall()}

    def collect(self, limit: int):
        local_clause = "AND pa.domain IS NULL" if self.local_only else ""

        query = text(f"""
            SELECT author_id, follower_count
            FROM popular_accounts pa
            WHERE pa.author_id != :account_id
              AND pa.follower_count >= :min_followers
              {local_clause}
            ORDER BY pa.follower_count DESC
            LIMIT :limit
        """)

        result = self.rw.execute(
            query,
            {
                "account_id": self.account_id,
                "min_followers": self.min_followers,
                "limit": limit * 3,
            },
        )

        candidates = result.fetchall()

        if not self.exclude_following:
            return [row[0] for row in candidates[:limit]]

        followed_ids = self._get_followed_ids()
        return [row[0] for row in candidates if row[0] not in followed_ids][:limit]
