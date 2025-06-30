from arango.database import StandardDatabase
from datetime import datetime, timedelta

from modules.herde.utils import parse_datetime

from ..base import Source


class PopularInSocialCircleSource(Source):
    """
    Collects statuses that are gaining traction within the near social circle of
    a user.
    """

    def __init__(
        self,
        db: StandardDatabase,
        account_id: int,
        max_hops: int = 2,
        language: str = "en",
        max_age: timedelta = timedelta(days=3),
    ):
        self.db = db
        self.account_id = account_id
        self.max_hops = max_hops
        self.language = language
        self.max_age = max_age

    def get_params(self):
        return {
            "language": self.language,
            "max_age": self.max_age.total_seconds(),
            "decay_rate": self.decay_rate,
        }

    def name(self):
        return "influence_propagation"

    def collect(self, limit: int):
        query = """
        FOR account IN 1..@max_hops OUTBOUND @source follows
            FOR status, engagement IN OUTBOUND account engaged
                FILTER status.language == @language AND engagement.event_time >= @max_age
                COLLECT status_id = status._key INTO groups
                LET count = LENGTH(groups)
                SORT count DESC
                LIMIT @limit
                RETURN { 
                    status_id: status_id, 
                    count: count, 
                }
        """

        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "limit": limit,
                "source": f"accounts/{self.account_id}",
                "max_hops": self.max_hops,
                "language": self.language,
                "max_age": parse_datetime(datetime.now() - self.max_age),
            },
        )

        for result in cursor:
            yield result

        cursor.close()
