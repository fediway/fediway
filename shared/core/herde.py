
from neo4j import GraphDatabase

from config import config

driver = GraphDatabase.driver(
    config.fediway.graph_url,
    auth=config.fediway.graph_auth
)

def get_herde_session():
    with driver.session() as session:
        yield session