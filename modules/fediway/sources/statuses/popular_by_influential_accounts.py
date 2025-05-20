
from datetime import timedelta, datetime

from ..base import Source

class PouplarStatusesByInfluentialAccountsSource(Source):
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