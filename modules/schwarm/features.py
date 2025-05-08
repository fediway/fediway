
from neo4j import Driver

class SchwarmInteractionFeatures():
    driver: Driver

    def __init__(self, driver: Driver):
        self.driver = driver

    def _run_query(self, query, **kwargs):
        with self.driver.session() as session:
            return session.run(query.strip(), **kwargs)

    def get_num_mentions(self, source_id: int, target_ids: list[int]) -> list[int]:
        query = '''
        MATCH (source:Account {id: $source_id})<-[:CREATED_BY]-(s:Status)-[:MENTIONS]->(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id AS target_id, COUNT(*) AS mentions
        '''

        results = self._run_query(query, source_id=source_id, target_ids=target_ids)
        results_map = {result['target_id']: result['mentions'] for result in results}

        return [results_map[target_id] for target_id in target_ids]

    def get_num_reblogs(self, source_id: int, target_ids: list[int]) -> list[int]:
        query = '''
        MATCH (source:Account {id: $source_id})-[:REBLOGS]->(s:Status)-[:CREATED_BY]->(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id AS target_id, COUNT(*) AS reblogs
        '''

        results = self._run_query(query, source_id=source_id, target_ids=target_ids)
        results_map = {result['target_id']: result['reblogs'] for result in results}

        return [results_map[target_id] for target_id in target_ids]

    def get_num_mutual_follows(self, src_id: int, tgt_ids: list[int]) -> list[int]:
        query = '''
        MATCH (src:Account {id: source_id})-[:FOLLOWS]->(mutual:Account)<-[:FOLLOWS]-(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id, COUNT(DISTINCT mutual) AS mutual_follows
        '''

        results = self._run_query(query, src_id=src_id, tgt_ids=tgt_ids)
        results_map = {result['target_id']: result['mutual_follows'] for result in results}

        return [results_map[target_id] for target_id in target_ids]

    def get_num_following_friends(self, src_id: int, tgt_ids: list[int]) -> list[int]:
        query = '''
        MATCH (src:Account {id: source_id})-[:FOLLOWS]->(friends:Account)-[:FOLLOWS]->(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id, COUNT(DISTINCT friends) AS following_friends
        '''

        results = self._run_query(query, src_id=src_id, tgt_ids=tgt_ids)
        results_map = {result['target_id']: result['following_friends'] for result in results}

        return [results_map[target_id] for target_id in target_ids]

class SchwarmTwoHopFeatures():
    driver: Driver

    def __init__(self, driver: Driver):
        self.driver = driver

    def _run_query(self, query, **kwargs):
        with self.driver.session() as session:
            return session.run(query.strip(), **kwargs)

    def get_num_favourites(self, source_id: int, target_ids: list[int]) -> list[int]:
        query = '''
        MATCH (source:Account {id: source_id})-[:FAVORITED]->(s1:Status)-[:CREATED_BY]->(middle:Account),
              (middle)-[:FAVORITED]->(s2:Status)-[:CREATED_BY]->(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id AS target_id, COUNT(*) AS two_hop_favourites
        '''

        results = self._run_query(query, source_id=source_id, target_ids=target_ids)
        results_map = {result['target_id']: result['two_hop_favourites'] for result in results}

        return [results_map[target_id] for target_id in target_ids]

    def get_num_follows(self, source_id: int, target_ids: list[int]) -> list[int]:
        query = '''
        MATCH (source:Account {id: source_id})-[:FOLLOWS]->(middle:Account)-[:FOLLOWS]->(target:Account)
        WHERE target.id IN $target_ids
        RETURN target.id AS target_id, COUNT(*) AS two_hop_follows
        '''

        results = self._run_query(query, source_id=source_id, target_ids=target_ids)
        results_map = {result['target_id']: result['two_hop_follows'] for result in results}

        return [results_map[target_id] for target_id in target_ids]