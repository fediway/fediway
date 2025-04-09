
from gqlalchemy import Memgraph, Node, Relationship, Field
from datetime import datetime
import math

# Connect to Memgraph
memgraph = Memgraph()

class Account(Node):
    id: int = Field(unique=True, index=True)
    community: int = Field(index=True)

class Status(Node):
    id: int = Field(unique=True, index=True)
    cluster: int = Field(index=True)

class Favourites(Relationship):
    pass

class SimilarTo(Relationship):
    similarity: float

memgraph.ensure_indexes()

def load_interactions(account_ids: list[int]):
    for account_id in account_ids:
        account = Account(id=account_id).save(memgraph)
        for status_id in range(user_id*100, user_id*100 + statuses_per_user):
            status = Status(id=status_id, cluster=-1).save(memgraph)

            Favourites(
                _start_node_id=account._id,
                _end_node_id=status._id,
                timestamp=datetime.now()
            ).save(memgraph)

@memgraph.query
def compute_similarities(batch_size=1000):
    """
    Memgraph query for similarity computation based on jaccard similarity
    """

    return list(memgraph.execute_and_fetch(f"""
        MATCH (a1:Account)-[:LIKES]->(t:Status)
        WITH a1, COLLECT(t.id) AS statuses1
        MATCH (a2:Account)-[:LIKES]->(t:Status)
        WHERE a1 <> a2
        WITH a1, a2, statuses1, COLLECT(t.id) AS statuses2
        WITH a1, a2, 
            SIZE([t IN statuses1 WHERE t IN statuses2]) AS intersection,
            SIZE(statuses1 + [t IN statuses2 WHERE NOT t IN statuses1]) AS union
        WHERE intersection > 0
        CREATE (a1)-[s:SIMILAR_TO {{
            similarity: intersection / toFloat(union),
            computed_at: '{datetime.now()}'
        }}]->(a2)
        RETURN COUNT(*) AS edges_created
    """))

@memgraph.query
def detect_communities():
    """
    Louvain community detection with post-processing
    """

    result = list(memgraph.execute_and_fetch("""
        CALL community_detection.get()
        YIELD node, community_id
        SET node.community = community_id
        RETURN COUNT(*)
    """))
    
    # Merge small communities
    memgraph.execute("""
        MATCH (a:Account)
        WITH a.community AS cid, COUNT(*) AS size
        WHERE size < 5
        MATCH (a:User {community: cid})
        SET a.community = -1
    """)

    return result
