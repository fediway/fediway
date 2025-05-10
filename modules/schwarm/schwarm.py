
from datetime import timedelta
from neo4j import Driver
import numpy as np
import time

from modules.mastodon.models import (
    Status, StatusStats, Account, Tag, StatusTag, Mention, Follow, Favourite
)

class Schwarm():
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
        CREATE INDEX ON :Account(indexable);
        CREATE INDEX ON :Status(id);
        CREATE INDEX ON :Status(language);
        CREATE INDEX ON :Status(created_at);
        CREATE INDEX ON :Tag(id);
        CREATE INDEX ON :Tag(rank);
        CREATE CONSTRAINT ON (a:Account) ASSERT a.id IS UNIQUE;
        CREATE CONSTRAINT ON (s:Status) ASSERT s.id IS UNIQUE;
        CREATE CONSTRAINT ON (t:Tag) ASSERT t.id IS UNIQUE;
        CREATE EDGE INDEX ON :FOLLOWS;
        CREATE EDGE INDEX ON :REBLOGS;
        """

        for query in queries.split(";"):
            if not query.strip():
                continue
            self._run_query(query)

    def add_tag(self, tag: Tag):
        query = """
        MERGE (t:Tag {id: $id})
        ON CREATE SET
            t.name = $name
        """

        self._run_query(query, id=tag.id, name=tag.name)

    def remove_tag(self, tag: Tag):
        query = """
        MATCH (t:Tag {id: $id})
        DELETE t;
        """

        self._run_query(query, id=tag.id)

    def add_account(self, account: Account):
        query = """
        MERGE (a:Account {id: $id})
        """

        self._run_query(query, id=account.id)

    def add_account_stats(self, stats: dict[str, int]):
        query = """
        MERGE (a:Account {id: $id})
        ON MATCH SET 
            a.avg_favs = $avg_favs,
            a.avg_replies = $avg_replies,
            a.avg_reblogs = $avg_reblogs;
        """

        self._run_query(
            query, 
            id=stats['account_id'],
            avg_favs=stats['avg_favourites_90d'],
            avg_replies=stats['avg_replies_90d'],
            avg_reblogs=stats['avg_reblogs_90d'],
        )

    def remove_account(self, account: Account):
        query = """
        MATCH (a:Account {id: $id})
        DELETE a;
        """

        self._run_query(query, id=account.id)

    def purge_old_statuses(self, max_age: timedelta):
        query = """
        MATCH (s:Status)
        WHERE s.created_at < $max_age
        DELETE s;
        """
        
        self._run_query(query, max_age=int(time.time()) - max_age.total_seconds())
    
    def add_status_stats(self, stats: StatusStats):
        query = """
        MERGE (s:Status {id: $id})
        ON MATCH SET 
            s.num_favs = $num_favs,
            s.num_replies = $num_replies,
            s.num_reblogs = $num_reblogs;
        """

        self._run_query(
            query, 
            id=stats.status_id,
            num_favs=stats.favourites_count,
            num_replies=stats.replies_count,
            num_reblogs=stats.reblogs_count,
        )

    def add_status_stats_batch(self, stats: list[StatusStats]):
        query = """
        UNWIND $stats as row
        MERGE (s:Status {id: row.id})
        ON MATCH SET 
            s.num_favs = row.num_favs,
            s.num_replies = row.num_replies,
            s.num_reblogs = row.num_reblogs;
        """

        self._run_query(
            query, 
            stats=[{
                'id': row.status_id,
                'num_favs': row.favourites_count,
                'num_replies': row.replies_count,
                'num_reblogs': row.reblogs_count,
            } for row in stats]
        )

    def add_status(self, status: Status):
        query = """
        MERGE (a:Account {id: $account_id})
        MERGE (s:Status {id: $id})
        ON CREATE SET 
            s.language = $language, 
            s.created_at = $created_at
        CREATE (a)-[:CREATED_BY]->(s)
        """

        created_at = status.created_at if type(status.created_at) == int else int(status.created_at.timestamp() * 1000)

        params = {
            'id': status.id,
            'account_id': status.account_id,
            'language': status.language,
            'created_at': created_at,
        }

        self._run_query(query, **params)

    def add_statuses(self, statuses: list[Status]):
        query = """
        UNWIND $statuses AS status
        MERGE (a:Account {id: status.account_id})
        MERGE (s:Status {id: status.id})
        ON CREATE SET 
            s.language = status.language, 
            s.created_at = status.created_at
        CREATE (a)-[:CREATED_BY]->(s)
        """

        statuses = [{
            'id': status.id,
            'account_id': status.account_id,
            'language': status.language,
            'created_at': status.created_at if type(status.created_at) == int else int(status.created_at.timestamp() * 1000),
        } for status in statuses]
        
        self._run_query(query, statuses=statuses)

    def add_status_tag(self, status_tag: StatusTag):
        query = """
        MERGE (s:Status {id: $status_id})
        MERGE (t:Tag {id: $tag_id})
        CREATE (s)-[:TAGS]->(t)
        """

        self._run_query(query, status_id=status_tag.status_id, tag_id=status_tag.tag_id)

    def add_status_tags(self, status_tags: list[StatusTag]):
        query = """
        UNWIND $status_tags as status_tag
        MERGE (s:Status {id: status_tag.status_id})
        MERGE (t:Tag {id: status_tag.tag_id})
        CREATE (s)-[:TAGS]->(t)
        """

        self._run_query(
            query, 
            status_tags=[{
                'status_id': status_tag.status_id,
                'tag_id': status_tag.tag_id,
            } for status_tag in status_tags]
        )

    def remove_status_tag(self, status_tag: StatusTag):
        query = """
        MATCH (s:Status {id: $status_id})-[r:TAGS]->(t:Tag {id: $tag_id})
        DELETE r;
        """

        self._run_query(query, status_id=status_tag.status_id, tag_id=status_tag.tag_id)

    def add_mention(self, mention: Mention):
        query = """
        MATCH (a:Account {id: $account_id})
        MATCH (s:Status {id: $status_id})
        MERGE (s)-[:MENTIONS]->(a);
        """

        self._run_query(
            query, 
            account_id=mention.account_id,
            status_id=mention.status_id,
        )

    def add_mentions(self, mentions: list[Mention]):
        query = """
        UNWIND $mentions as mention
        MATCH (a:Account {id: mention.account_id})
        MATCH (s:Status {id: mention.status_id})
        MERGE (s)-[:MENTIONS]->(a);
        """

        self._run_query(
            query, 
            mentions=[{
                'account_id': mention.account_id,
                'status_id': mention.status_id,
            } for mention in mentions]
        )

    def remove_mention(self, mention: Mention):
        query = """
        MATCH (s:Status {id: $status_id})-[r:MENTIONS]->(a:Account {id: $account_id});
        DELETE r;
        """

        self._run_query(
            query, 
            account_id=mention.account_id,
            status_id=mention.status_id,
        )
        
    def remove_status(self, status: Status):
        query = """
        MATCH (s:Status {id: $id})
        DELETE s;
        """

        self._run_query(query, id=status.id)
    
    def add_reblog(self, reblog: Status):
        query = """
        MATCH (a:Account {id: $account_id})
        MATCH (s:Status {id: $reblog_of_id})
        CREATE (a)-[:REBLOGS]->(s);
        """

        self._run_query(
            query, 
            account_id=reblog.account_id,
            reblog_of_id=reblog.reblog_of_id,
        )

    def add_reblogs(self, reblogs: list[Status]):
        query = """
        UNWIND $reblogs AS reblog
        MATCH (a:Account {id: reblog.account_id})
        MATCH (s:Status {id: reblog.reblog_of_id})
        CREATE (a)-[:REBLOGS]->(s);
        """

        self._run_query(
            query, 
            reblogs=[{
                'account_id': reblog.account_id,
                'reblog_of_id': reblog.reblog_of_id,
            } for reblog in reblogs]
        )

    def remove_reblog(self, status: Status):
        query = """
        MATCH (a:Account {id: $account_id})-[r:REBLOGS]->(s:Status {id: $reblog_of_id})
        DELETE r;
        """

        self._run_query(
            query, 
            account_id=status.account_id,
            reblog_of_id=status.reblog_of_id,
        )

    def add_favourite(self, favourite: Favourite):
        query = """
        MATCH (a:Account {id: $account_id})
        MATCH (s:Status {id: $status_id})
        MERGE (a)-[:FAVOURITES]->(s)
        """

        self._run_query(query, account_id=favourite.account_id, status_id=favourite.status_id)

    def add_favourites(self, favourites: list[Favourite]):
        query = """
        UNWIND $favs AS fav
        MATCH (a:Account {id: fav.account_id})
        MATCH (s:Status {id: fav.status_id})
        MERGE (a)-[:FAVOURITES]->(s)
        """

        self._run_query(
            query, 
            favs=[{
                'account_id': fav.account_id,
                'status_id': fav.status_id,
            } for fav in favourites]
        )

    def remove_favourite(self, favourite: Favourite):
        query = """
        MATCH (a:Account {id: $account_id})-[r:FAVOURITES]->(s:Status {id: $status_id})
        DELETE r;
        """

        self._run_query(query, account_id=favourite.account_id, status_id=favourite.status_id)

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
        WITH timestamp() / 1000 AS now
        MATCH (a:Account)-[:CREATED_BY]->(s:Status)
        WHERE 
            a.rank IS NOT NULL 
        RETURN s.created_at, now
        LIMIT 10
        """

        # query = """
        # WITH timestamp() AS now
        # MATCH (a:Account)-[:CREATED_BY]->(s:Status {language: $language})
        # WITH a, s, (now - s.created_at) / 86400 AS age_days
        # WITH 
        #     a.id as account_id, 
        #     s.id AS status_id,
        #     // Content virality (60% weight)
        #     0.6  * (s.num_favs + 2 * s.num_reblogs) * 10 / (a.avg_favs + 2 * a.avg_reblogs + 1) + 
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

    def compute_tag_rank(self):
        query = """
        CALL pagerank.get()
        YIELD node, rank
        MATCH (t:Tag {id: node.id})
        SET t.rank = rank
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