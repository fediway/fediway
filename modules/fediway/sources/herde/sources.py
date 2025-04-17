
from datetime import timedelta

from ..base import Source
from .herde import Herde

class TrendingStatusesByInfluentialUsers(Herde, Source):
    def __init__(self, driver, language: str = 'en'):
        super().__init__(driver)
        self.language = language

    def compute_scores(self):
        pass


    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000000 AS now
        MATCH (a:Account)-[:CREATED_BY]->(s:Status {language: $language})
        WHERE 
            a.rank IS NOT NULL 
        // AND a.avg_favs > 1 
        // AND a.avg_reblogs > 1 
        AND s.num_favs > 0 
        AND s.num_reblogs > 0
        WITH a, s, (now - s.created_at) / 86400 AS age_days
        WITH a, s, age_days,
            a.rank * (s.num_favs + 2 * s.num_reblogs) as score // / (a.avg_favs + 2 * a.avg_reblogs) AS score
        ORDER BY a.id, score DESC
        WITH a.id AS account_id, collect([s.id, score])[0] AS top_status
        RETURN account_id, top_status[0] AS status_id, top_status[1] AS score
        ORDER BY score DESC
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit)

            for result in list(results):
                yield result['status_id']

class TrendingTagsSource(Herde, Source):
    def __init__(self, driver, language: str = 'en', max_age = timedelta(days=3)):
        super().__init__(driver)
        self.language = language
        self.max_age = max_age

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000000 AS now
        MATCH (s:Status {language: $language})-[:TAGS]->(t:Tag)
        WHERE 
            t.rank IS NOT NULL
        AND s.created_at > $max_age
        WITH t, s, (now - s.created_at) / 86400 AS age_days
        WITH t, s, SUM((s.num_favs + 2 * s.num_reblogs) * EXP(-0.1 * age_days)) AS engagement_score
        WITH t, s, t.rank * engagement_score as score
        ORDER BY t.id, score DESC
        RETURN t.id as tag_id, score
        ORDER BY score DESC
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit, max_age=self.max_age.total_seconds())

            for result in list(results):
                yield result['tag_id']