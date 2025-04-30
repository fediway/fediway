
from datetime import timedelta, datetime

from .base import Source

class TrendingStatusesByInfluentialUsers(Source):
    def __init__(self, driver, language: str = 'en', max_age = timedelta(days=3)):
        self.driver = driver
        self.language = language
        self.max_age = max_age

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (a:Account)-[:CREATED_BY]->(s:Status)
        WHERE 
            a.rank IS NOT NULL 
        AND s.created_at > $max_age
        // AND a.avg_favs > 1 
        // AND a.avg_reblogs > 1 
        // AND s.num_favs > 0 
        // AND s.num_reblogs > 0
        WITH a, s, (now - s.created_at) / 86400 AS age_days
        WITH a, s, age_days,
            a.rank * EXP(-age_days) * ((s.num_favs + 1) * (s.num_reblogs + 1)) * 10 / ((a.avg_favs + 1) * (a.avg_reblogs + 1)) AS score
        ORDER BY a.id, score DESC
        WITH a.id AS account_id, collect([s.id, score])[0] AS top_status
        RETURN account_id, top_status[0] AS status_id, top_status[1] AS score
        ORDER BY score DESC
        LIMIT $limit;
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit, max_age=max_age)

            for result in list(results):
                yield result['status_id']

class TrendingTagsSource(Source):
    def __init__(self, driver, language: str = 'en', max_age = timedelta(days=3)):
        self.driver = driver
        self.language = language
        self.max_age = max_age

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
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

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit, max_age=max_age)

            for result in list(results):
                yield result['tag_id']

class CollaborativeFilteringSource(Source):
    def __init__(self, driver, account_id: int, language: str = 'en', max_age = timedelta(days=3)):
        self.driver = driver
        self.language = language
        self.account_id = account_id

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        MATCH (me:Account {id: $account_id})-[:FAVOURITES]->(s:Status)<-[:FAVOURITES]-(them:Account)
        WITH me, them, COUNT(s) AS mutual_favourites
        ORDER BY mutual_favourites DESC
        // RETURN them.id as account_id, mutual_favourites
        MATCH (them)-[:FAVOURITES]->(recommendation:Status)
        OPTIONAL MATCH (me)-[already_favourited:FAVOURITES]->(recommendation)
        WITH recommendation, already_favourited
        WHERE already_favourited is NULL
        RETURN recommendation.id as status_id
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(query, language=self.language, account_id=self.account_id, limit=limit)

            for result in list(results):
                yield result['status_id']

class FolloweeActivitySource(Source):
    def __init__(self, driver, language: str = 'en'):
        self.driver = driver
        self.language = language

    def collect(self, limit: int, account_id: int):
        query = """
        MATCH (me:Account {id: $account_id})-[:FOLLOWS]->(followed:Account)-[:FAVOURITES|CREATED_BY]->(s:Status)
        WHERE NOT (me)-[:LIKES]->(s)
        RETURN s.id as status_id
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(query, language=self.language, account_id=account_id, limit=limit)

            for result in list(results):
                yield result['status_id']