from datetime import timedelta

from ..base import Source


class CollaborativeFilteringSource(Source):
    def __init__(
        self, driver, account_id: int, language: str = "en", max_age=timedelta(days=3)
    ):
        self.driver = driver
        self.language = language
        self.account_id = account_id

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        MATCH (me:Account {id: $account_id})-[:FAVOURITES|REBLOGS]->(s:Status)<-[:FAVOURITES|REBLOGS]-(them:Account)
        WITH me, them, COUNT(s) AS mutual_interactions
        ORDER BY mutual_interactions DESC
        // RETURN them.id as account_id, mutual_interactions
        MATCH (them)-[:FAVOURITES|REBLOGS]->(recommendation:Status)
        OPTIONAL MATCH (me)-[already_interacted:FAVOURITES|REBLOGS]->(recommendation)
        WITH recommendation, already_interacted
        WHERE already_interacted is NULL
        RETURN recommendation.id as status_id
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(
                query, language=self.language, account_id=self.account_id, limit=limit
            )

            for result in list(results):
                yield result["status_id"]
