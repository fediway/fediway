
from qdrant_client import models
import typer

from config import config

app = typer.Typer(help="Qdrant commands.")

COLLECTIONS = [
    'status_embeddings',
    'latest_account_favourites_embeddings',
    'latest_account_reblogs_embeddings',
    'latest_account_replies_embeddings',
]

@app.command("migrate")
def migrate():
    from app.core.qdrant import client

    for collection in COLLECTIONS:
        if client.collection_exists(collection):
            continue
        
        vectors_config = models.VectorParams(size=config.embed.dim(), distance=models.Distance.COSINE)
        client.create_collection(collection_name=collection, vectors_config=vectors_config)

        typer.echo(f"✅ Created '{collection}' collection.")

@app.command("purge")
def purge():
    from app.core.qdrant import client
    
    for collection in COLLECTIONS:
        if not client.collection_exists(collection):
            continue
        
        client.delete_collection(collection_name=collection)

        typer.echo(f"✅ Deleted '{collection}' collection.")