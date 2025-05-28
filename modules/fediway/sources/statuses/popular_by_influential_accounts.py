from datetime import datetime, timedelta
from redis import Redis
from neo4j import Driver

from ..base import RedisSource


class PouplarByInfluentialAccountsSource(RedisSource):
    def __init__(
        self,
        r: Redis,
        driver: Driver,
        language: str = "en",
        top_n: int = 5000,
        decay_rate: float = 1.0,
        ttl: timedelta = timedelta(seconds=60),
    ):
        super().__init__(r=r, ttl=ttl)

        self.driver = driver
        self.language = language
        self.top_n = top_n
        self.decay_rate = decay_rate

    def group(self):
        return "popular_by_influential_accounts"

    def name(self):
        return f"popular_by_influential_accounts[l={self.language},d={self.decay_rate}]"

    def compute(self):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (s:Status {language: $language})
        WHERE s.score IS NOT NULL
        WITH s, (now - s.created_at) / 86400 AS age_days
        WITH s, EXP(-$decay_rate * age_days) * s.score as score
        ORDER BY score DESC
        RETURN s.id as status_id, score
        LIMIT $top_n;
        """

        with self.driver.session() as session:
            results = session.run(
                query,
                language=self.language,
                decay_rate=self.decay_rate,
                top_n=self.top_n,
            )

            for result in results:
                yield result["status_id"]
