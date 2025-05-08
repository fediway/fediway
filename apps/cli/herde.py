
from datetime import datetime, timedelta
from loguru import logger
import typer
import time

from config import config

app = typer.Typer(help="Schwarm commands.")

def get_client():
    from arango import ArangoClient
    return ArangoClient(hosts=config.fediway.arango_hosts)

@app.command("create-db")
def create_db():
    client = get_client()

    sys_db = client.db(
        "_system", 
        username=config.fediway.arango_user, 
        password=config.fediway.arango_pass
    )

    if not sys_db.has_database(config.fediway.arango_name):
        sys_db.create_database(config.fediway.arango_name)
        typer.echo(f"✅ Created {config.fediway.arango_name} arango database.")
    else:
        typer.echo(f"Arango database {config.fediway.arango_name} already exists.")

@app.command("migrate")
def migrate():
    from shared.core.herde import db

    if not db.has_graph(config.fediway.arango_graph):
        graph = db.create_graph(config.fediway.arango_graph)
    else:
        graph = db.graph(config.fediway.arango_graph)

    if not graph.has_vertex_collection("accounts"):
        accounts = graph.create_vertex_collection("accounts")

    if not graph.has_vertex_collection("statuses"):
        statuses = graph.create_vertex_collection("statuses")

    if not graph.has_vertex_collection("tags"):
        tags = graph.create_vertex_collection("tags")

    graph.create_edge_definition(
        edge_collection='follows',
        from_vertex_collections=['accounts'],
        to_vertex_collections=['accounts']
    )

    graph.create_edge_definition(
        edge_collection='tagged',
        from_vertex_collections=['statuses'],
        to_vertex_collections=['tags']
    )

    for edge in ['favourited', 'reblogged', 'replied', 'created']:
        graph.create_edge_definition(
            edge_collection=edge,
            from_vertex_collections=['accounts'],
            to_vertex_collections=['statuses']
        )