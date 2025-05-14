
from neo4j.exceptions import ServiceUnavailable
from datetime import timedelta, datetime

from .base import Source, RedisSource

class TrendingStatusesByInfluentialUsers(Source):
    def __init__(
        self, 
        driver, 
        language: str = 'en', 
        max_age: timedelta = timedelta(days=3),
        top_n: int = 5000,
        alpha: float = 1.0
    ):
        self.driver = driver
        self.language = language
        self.max_age = max_age
        self.top_n = top_n
        self.alpha = alpha

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (s:Status {language: $language})
        WHERE 
            s.score IS NOT NULL
        AND s.created_at > $max_age
        WITH s, now
        ORDER BY s.score DESC
        LIMIT $top_n
        WITH s, (now - s.created_at) / 86400 AS age_days
        WITH s, EXP(-$alpha * age_days) * s.score as score
        ORDER BY score DESC
        RETURN s.id as status_id, score
        LIMIT $limit;
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(
                query, 
                language=self.language, 
                alpha=self.alpha,
                limit=limit, 
                top_n=self.top_n,
                max_age=max_age,
            )

            for result in results:
                yield result['status_id']

class TrendingStatusesByInfluentialUsers(Source):
    def __init__(
        self, 
        driver, 
        language: str = 'en', 
        max_age: timedelta = timedelta(days=3),
        top_n: int = 5000,
        alpha: float = 1.0
    ):
        self.driver = driver
        self.language = language
        self.max_age = max_age
        self.top_n = top_n
        self.alpha = alpha

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (s:Status {language: $language})
        WHERE 
            s.score IS NOT NULL
        AND s.created_at > $max_age
        WITH s, now
        ORDER BY s.score DESC
        LIMIT $top_n
        WITH s, (now - s.created_at) / 86400 AS age_days
        WITH s, EXP(-$alpha * age_days) * s.score as score
        ORDER BY score DESC
        RETURN s.id as status_id, score
        LIMIT $limit;
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(
                query, 
                language=self.language, 
                alpha=self.alpha,
                limit=limit, 
                top_n=self.top_n,
                max_age=max_age,
            )

            for result in results:
                yield result['status_id']

class TrendingStatusesInCommunity(Source):
    def __init__(self, driver, account_id: int, alpha: float = 0.1):
        self.driver = driver
        self.account_id = account_id
        self.alpha = alpha

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (u:Account {id: $account_id})
        MATCH (a:Account)-[:CREATED_BY]->(s:Status {community_id: u.community_id})
        WHERE 
            a.rank IS NOT NULL 
        AND s.num_favs > 0 
        AND s.num_reblogs > 0
        WITH a, s, (now - s.created_at) / 86400 AS age_days
        WITH a, s, age_days,
            a.rank * EXP(-$alpha * age_days) * ((s.num_favs + 1) * 0.5 + (s.num_reblogs + 1) * 2) as score
        ORDER BY a.id, score DESC
        WITH a.id AS account_id, collect([s.id, score])[0] AS top_status
        RETURN account_id, top_status[0] AS status_id, top_status[1] AS score
        ORDER BY score DESC
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(
                query, 
                account_id=self.account_id, 
                limit=limit, 
                alpha=self.alpha
            )

            for result in list(results):
                yield result['status_id']

class TrendingStatusesByTagsInCommunity(Source):
    def __init__(self, driver, account_id: int, alpha: float = 0.1):
        self.driver = driver
        self.account_id = account_id
        self.alpha = alpha

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (u:Account {id: $account_id})
        MATCH (t:Tag {community_id: u.community_id})-[:TAGGED]->(s:Status)
        WHERE 
            t.rank IS NOT NULL 
        AND s.num_favs > 0 
        AND s.num_reblogs > 0
        WITH t, s, (now - s.created_at) / 86400 AS age_days
        WITH t, s, age_days,
            t.rank * EXP(-$alpha * age_days) * ((s.num_favs + 1) * 0.5 + (s.num_reblogs + 1) * 2) as score
        ORDER BY t.id, score DESC
        WITH t.id AS tag_id, collect([s.id, score])[0] AS top_status
        RETURN tag_id, top_status[0] AS status_id, top_status[1] AS score
        ORDER BY score DESC
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(
                query, 
                account_id=self.account_id, 
                limit=limit, 
                alpha=self.alpha
            )

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

class MostInteractedByAccountsSource(Source):
    '''
    Collects statuses that where most interacted with by a list of accounts.
    '''

    def __init__(
        self, 
        driver, 
        account_ids: list[int],
        alpha: float = 0.1
    ):
        self.driver = driver
        self.account_ids = account_ids
        self.alpha = alpha

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (a:Account)-[:FAVOURITES]->(s:Status)
        // WHERE a.id IN $account_ids
        WITH s, (now - s.created_at) / (86400 * 1000) AS age_days, now
        WITH s, SUM(EXP(-$alpha * age_days)) AS score
        RETURN s.id as status_id, score
        ORDER BY score DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            results = session.run(
                query, 
                account_ids=self.account_ids, 
                alpha=self.alpha,
                limit=limit, 
            )

            for result in list(results):
                yield result['status_id']