from arango.database import StandardDatabase
from datetime import datetime, timedelta

from modules.herde.utils import parse_datetime

from ..base import Source


class NewestInNetworkSource(Source):
    """
    Collects newest statuses from following accounts.
    """

    def __init__(
        self,
        db: StandardDatabase,
        account_id: int,
    ):
        self.db = db
        self.account_id = account_id

    def group(self):
        return "newest_in_network"

    def name(self):
        return f"newest_in_network[l={self.language},h={self.max_hops},a={self.max_age.total_seconds()}]"

    def collect(self, limit: int):
        query = """
        FOR account IN 1..1 OUTBOUND @source follows
            FOR status IN OUTBOUND account created
                SORT status.created_at DESC
                LIMIT @limit
                RETURN { 
                    status_id: status._key, 
                    created_at: status.created_at, 
                }
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
