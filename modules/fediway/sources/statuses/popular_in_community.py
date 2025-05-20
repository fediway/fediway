from ..base import Source


class PopularInCommunitySource(Source):
    def __init__(self, driver, account_id: int, decay_rate: float = 0.1):
        self.driver = driver
        self.account_id = account_id
        self.decay_rate = decay_rate

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
            a.rank * EXP(-$decay_rate * age_days) * ((s.num_favs + 1) * 0.5 + (s.num_reblogs + 1) * 2) as score
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
                decay_rate=self.decay_rate,
            )

            for result in list(results):
                yield result["status_id"]
