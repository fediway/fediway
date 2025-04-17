
from .herde import Herde
from .sources import TrendingStatusesByInfluentialUsers, TrendingTagsSource

from datetime import datetime
import math

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
