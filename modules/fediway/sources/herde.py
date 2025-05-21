from datetime import datetime, timedelta

from arango.database import StandardDatabase

from .base import Source


class CollaborativeFilteringSource(Source):
    def __init__(
        self, db: StandardDatabase, language: str = "en", max_age=timedelta(days=3)
    ):
        self.db = db
        self.language = language
        self.max_age = max_age

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(
                query, language=self.language, limit=limit, max_age=max_age
            )

            for result in list(results):
                yield result["status_id"]
