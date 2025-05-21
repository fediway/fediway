from datetime import datetime, timedelta

from arango.database import StandardDatabase

from modules.herde.utils import parse_datetime

from ..base import Source


class RecentlyEngagedSource(Source):
    """
    Suggests accounts based on recent engagements.
    """

    def __init__(self, db: StandardDatabase, account_id: int, max_age: timedelta):
        self.db = db
        self.account_id = account_id
        self.max_age = max_age

    def collect(self, limit: int):
        query = """
        FOR engagement IN UNION(
            FOR e IN favourited
                FILTER e._from == @source
                FILTER e.created_at >= @max_age
                RETURN e,
            FOR e IN reblogged
                FILTER e._from == @source
                FILTER e.created_at >= @max_age
                RETURN e,
            FOR e IN replied
                FILTER e._from == @source
                FILTER e.created_at >= @max_age
                RETURN e
        )
            LET target = FIRST(
                FOR v IN INBOUND engagement._to created
                    RETURN v
            )

            LIMIT @limit
            RETURN { target: target._key }
        """

        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "limit": limit,
                "max_age": parse_datetime(datetime.now() - self.max_age),
                "source": f"accounts/{self.account_id}",
            },
        )

        for result in cursor:
            yield result["target"]

        cursor.close()
