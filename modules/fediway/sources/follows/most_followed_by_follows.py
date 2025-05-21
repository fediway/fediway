from arango.database import StandardDatabase

from ..base import Source


class MostFollowedByFollowsSource(Source):
    """
    Suggests accounts are most followed by the followers of a given account.
    """

    def __init__(self, db: StandardDatabase, account_id: int):
        self.db = db
        self.account_id = account_id

    def collect(self, limit: int):
        query = """
        FOR follower IN INBOUND @source follows
            FOR candidate IN OUTBOUND follower follows
                FILTER candidate._key != @source
                COLLECT target = candidate WITH COUNT INTO freq
                SORT freq DESC
                LIMIT @limit
                RETURN { target: target._key, freq }
        """

        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "limit": limit,
                "source": f"accounts/{self.account_id}",
            },
        )

        for result in cursor:
            yield result

        cursor.close()
