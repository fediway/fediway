from ..base import Source


class PopularInCommunitySource(Source):
    def __init__(
        self,
        driver,
        account_id: int,
        decay_rate: float = 0.1,
        top_n: int = 5000,
    ):
        self.driver = driver
        self.account_id = account_id
        self.decay_rate = decay_rate
        self.top_n = top_n

    def group(self):
        return "popular_in_community"

    def name(self):
        return f"popular_in_community[d={self.decay_rate}]"

    def collect(self, limit: int):
        query = """
        WITH timestamp() / 1000 AS now
        MATCH (u:Account {id: $account_id})
        MATCH (s:Status {community_id: u.community_id})
        WHERE 
            s.score IS NOT NULL
        WITH s, now
        ORDER BY s.score DESC
        LIMIT $top_n
        WITH s, (now - s.created_at) / 86400000 AS age_days
        WITH s, EXP(-$decay_rate * age_days) * s.score as score
        ORDER BY score DESC
        RETURN s.id as status_id, score
        LIMIT $limit;
        """

        with self.driver.session() as session:
            results = session.run(
                query,
                account_id=self.account_id,
                limit=limit,
                decay_rate=self.decay_rate,
                top_n=self.top_n,
            )

            for result in list(results):
                yield result["status_id"]
