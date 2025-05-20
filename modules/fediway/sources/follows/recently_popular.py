from datetime import datetime, timedelta
from arango.database import StandardDatabase

from modules.herde.utils import parse_datetime

from ..base import Source


class RecentlyPopularSource(Source):
    """
    Provides the top accounts by pagerank score based on recent statuses and
    engagements via memgraph. Only accounts that recently created statuses in a
    given language are returned.
    """

    def __init__(self, driver, account_id: int, language: str = "en"):
        self.driver = driver
        self.account_id = account_id
        self.language = language

    def collect(self, limit: int):
        query = """
        MATCH (source:Account {id: $account_id})
        MATCH (target:Account)-[CREATED]->(s:Status {language: $language})
        WHERE target.rank IS NOT NULL
          AND target <> source
          AND NOT EXISTS((source)-[:FOLLOWS]->(target))
        RETURN DISTINCT target.id as account_id, target.rank as rank
        ORDER BY target.rank DESC
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(
                query, limit=limit, language=self.language, account_id=self.account_id
            )

            for result in list(results):
                yield result["account_id"]
