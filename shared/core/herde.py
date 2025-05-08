
from neo4j import GraphDatabase
from arango import ArangoClient

from config import config

client = ArangoClient(hosts=config.fediway.arango_hosts)

db = client.db(
    config.fediway.arango_name, 
    username=config.fediway.arango_user,
    password=config.fediway.arango_pass,
)

graph = db.graph(config.fediway.arango_graph)