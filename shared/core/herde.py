from neo4j import GraphDatabase
from arango import ArangoClient, ServerConnectionError
from loguru import logger

from config import config

client = ArangoClient(hosts=config.fediway.arango_hosts)

db = None
try:
    db = client.db(
        config.fediway.arango_name,
        username=config.fediway.arango_user,
        password=config.fediway.arango_pass,
        verify=True,
    )
except ServerConnectionError as e:
    logger.error(e)

graph = None
if db is not None and db.has_graph(config.fediway.arango_graph):
    graph = db.graph(config.fediway.arango_graph)
