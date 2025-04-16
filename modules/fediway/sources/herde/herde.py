
from neo4j import Driver
import numpy as np

from app.modules.models import Status, Account

class Herde():
    driver: Driver

    def __init__(self, driver: Driver):
        self.driver = driver

    def _run_query(self, query, **kwargs):
        with self.driver.session() as session:
            return session.run(query.strip(), **kwargs)

    def setup(self):
        queries = """
        CREATE INDEX ON :Account(id);
        CREATE INDEX ON :Account(rank);
        CREATE INDEX ON :Status(language);
        CREATE INDEX ON :Status(created_at);
        CREATE CONSTRAINT ON (a:Account) ASSERT a.id IS UNIQUE;
        CREATE CONSTRAINT ON (s:Status) ASSERT s.id IS UNIQUE;
        CREATE EDGE INDEX ON :FOLLOWS;
        """

        for query in queries.split(";"):
            if not query.strip():
                continue
            self._run_query(query)

    def add_account(self, account: Account):
        query = """
        MERGE (a:Account {id: $id})
        ON CREATE SET 
            a.avg_favs = $avg_favs,
            a.avg_replies = $avg_replies,
            a.avg_reblogs = $avg_reblogs
        """

        favs = [s.stats.favourites_count for s in account.statuses if s.stats is not None]
        avg_favs = 0.
        if len(favs) > 0:
            avg_favs = float(np.mean(favs))

        replies = [s.stats.replies_count for s in account.statuses if s.stats is not None]
        avg_replies = 0.
        if len(favs) > 0:
            avg_replies = float(np.mean(replies))

        reblogs = [s.stats.reblogs_count for s in account.statuses if s.stats is not None]
        avg_reblogs = 0.
        if len(favs) > 0:
            avg_reblogs = float(np.mean(reblogs))

        self._run_query(
            query, 
            id=account.id,
            avg_favs=avg_favs,
            avg_replies=avg_replies,
            avg_reblogs=avg_reblogs,
        )

    def add_follow(self, source_id:int, target_id: int):
        query = """
        MATCH (a:Account {id: $source_id})
        MATCH (b:Account {id: $target_id})
        MERGE (a)-[:FOLLOWS]->(b);
        """

        self._run_query(
            query, 
            source_id=source_id,
            target_id=target_id,
        )

    def add_status(self, status: Status):
        query = """
        MATCH (a:Account {id: $account_id})
        MERGE (s:Status {id: $id})
        ON CREATE SET 
            s.language = $language, 
            s.created_at = $created_at,
            s.num_favs = $num_favs,
            s.num_replies = $num_replies,
            s.num_reblogs = $num_reblogs
        CREATE (a)-[:CREATED_BY]->(s);
        """

        self._run_query(
            query, 
            id=status.id,
            account_id=status.account_id,
            language=status.language,
            created_at=status.created_at.timestamp(),
            num_favs=status.stats.favourites_count,
            num_replies=status.stats.replies_count,
            num_reblogs=status.stats.reblogs_count,
        )

    def add_statuses(self, statuses: list[Status]):
        query = """
        UNWIND $batch AS status
        MATCH (a:Account {id: status.account_id})
        MERGE (s:Status {id: status.id})
        ON CREATE SET 
            s.language = status.language, 
            s.created_at = status.created_at,
            s.num_favs = status.num_favs,
            s.num_replies = status.num_replies,
            s.num_reblogs = status.num_reblogs
        CREATE (a)-[:CREATED_BY]->(s)
        """

        self._run_query(
            query, 
            batch = [{
                'id': status.id,
                'account_id': status.account_id,
                'language': status.language,
                'created_at': status.created_at.timestamp(),
                'num_favs': status.stats.favourites_count,
                'num_replies': status.stats.replies_count,
                'num_reblogs': status.stats.reblogs_count,
            } for status in statuses]
        )

    def add_favourite(self, account_id: int, status_id: int):
        query = """
        MATCH (a:Account {id: $account_id})
        MATCH (s:Status {id: $status_id})
        MERGE (a)-[:FAVOURITES]->(s)
        """

        self._run_query(
            query, 
            account_id=account_id,
            status_id=status_id,
        )

    # def get_relevant_statuses(self, language, limit=10):
    #     query = """
    #     MATCH (a:Account)-[:CREATED_BY]->(s:Status {language: $language})
    #     // MATCH (c:Community {id: a.community_id})

    #     WITH 
    #         a.community_id as community_id, 
    #         s.id as status_id,
    #         a.rank * (s.num_favs + 2 * s.num_reblogs) / (a.avg_favs + 2 * a.avg_reblogs) AS score

    #     ORDER BY community_id, score DESC
    #     WITH community_id, COLLECT({status_id: status_id, score: score})[..5] AS community_top // 5 per community
        
    #     UNWIND community_top AS top
    #     RETURN top.status_id AS status_id, top.score
    #     LIMIT $limit
    #     """

    #     return self.session.run(
    #         query, 
    #         language=language, 
    #         limit=limit
    #     )

    def get_relevant_statuses(self, language, limit=10):

        query = """
        MATCH (a:Account)-[:CREATED_BY]->(s:Status {language: $language})
        WITH a, s, 
            a.rank * (s.num_favs + 2 * s.num_reblogs) / (a.avg_favs + 2 * a.avg_reblogs) AS score
        ORDER BY a.id, score DESC
        WITH a.id AS account_id, collect([s.id, score])[0] AS top_status
        RETURN account_id, top_status[0] AS status_id, top_status[1] AS score
        ORDER BY score DESC
        LIMIT $limit;
        """
        # query = """
        # WITH timestamp() AS now
        # MATCH (a:Account)-[:CREATED_BY]->(s:Status {language: $language})
        # WITH a, s, (now - s.created_at) / 86400 AS age_days
        # WITH 
        #     a.id as account_id, 
        #     s.id AS status_id,
        #     // Content virality (60% weight)
        #     0.6  * (s.num_favs + 2 * s.num_reblogs) * 10 / (a.avg_favs + 2 * a.avg_reblogs) + 
        #     0.5 * a.rank
        #     AS score
        #     // Cross-community appeal (25% weight)
        #     // 0.25 * COALESCE(s.diversity_score, 0) 
        #     // Author authority (15% weight)
        #     // a.rank * (s.num_favs + 2 * s.num_reblogs) / (a.avg_favs + 2 * a.avg_reblogs) AS score
        # ORDER BY account_id, score DESC
        # WITH account_id, collect([status_id, score])[0] AS top_status
        # RETURN account_id, top_status[0] AS status_id, top_status[1] AS score
        # LIMIT $limit
        # """
        with self.driver.session() as session:
            results = session.run(
                query, 
                language=language, 
                limit=limit
            )
            for result in results:
                yield result

    def get_authorities(self):
        query = """
        MATCH (a:Account)-[:FOLLOWS]->(b:Account)
        WITH gds.graph.project('follow_graph', 'Account', 'FOLLOWS') AS graph
        CALL gds.pageRank.stream('follow_graph')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).id AS account_id, score
        ORDER BY score DESC
        LIMIT 10
        """

        with self.driver.session() as session:
            result = session.run(query)

            return [record for record in result]

    def compute_account_rank(self):
        query = """
        CALL pagerank.get()
        YIELD node, rank
        MATCH (a:Account {id: node.id})
        SET a.rank = rank
        """
        self._run_query(query)

    # def compute_engagement_baselines(self):
    #     query = """
    #     MATCH (a:Account)-[:CREATED_BY]->(s:Status)
    #     OPTIONAL MATCH (s)<-[fav:FAVOURITES]-()
    #     WITH a, s, COUNT(fav) AS fav_count
    #     WITH a, AVG(fav_count) AS avg_fav
    #     SET a.avg_fav = avg_fav
    #     """

    #     self.driver.execute_query(query)

    def compute_diversity_scores(self):
        """Measure cross-community appeal using entropy"""
        query = """
        MATCH (s:Status)<-[:FAVOURITES]-(a:Account)
        WITH s, a.community_id AS comm, COUNT(*) AS interactions
        WITH s, 
            COLLECT(interactions) AS comm_counts,
            SUM(interactions) AS total
        WITH s, 
            REDUCE(ent=0.0, c IN comm_counts | 
            ent - (c/total) * log(c/total)) AS entropy
        SET s.diversity_score = entropy
        """

        self._run_query(query)

    def detect_communities(self):
        query = """
        CALL community_detection.get()
        YIELD node, community_id
        WITH node AS a, community_id
        WHERE "Account" IN LABELS(a)
        SET a.community_id = community_id
        """

        self._run_query(query)