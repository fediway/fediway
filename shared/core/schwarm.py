
from neo4j import GraphDatabase

from config import config

driver = GraphDatabase.driver(
    config.fediway.memgraph_url,
    auth=config.fediway.memgraph_auth
)

def get_schwarm_session():
    with driver.session() as session:
        yield session