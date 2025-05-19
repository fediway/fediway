
from datetime import datetime, timedelta

from ..base import Source

class RecentlyPopularSource(Source):
    def __init__(self, driver, language: str = 'en', max_age = timedelta(days=3)):
        self.driver = driver
        self.language = language
        self.max_age = max_age

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (s:Status {language: $language})-[:TAGS]->(t:Tag)
        WHERE t.rank IS NOT NULL
          AND s.created_at > $max_age
        ORDER BY t.rank DESC
        RETURN t.id as tag_id, t.rank as rank
        LIMIT $limit;
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit, max_age=max_age)

            for result in list(results):
                yield result['tag_id']