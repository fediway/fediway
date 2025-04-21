
from qdrant_client import models
import typer

from app.core.embed import text_embeder
from app.core.qdrant import client
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
    for collection in COLLECTIONS:
        if client.collection_exists(collection):
            continue
        
        vectors_config = models.VectorParams(size=text_embeder.dim(), distance=models.Distance.COSINE)
        client.create_collection(collection_name=collection, vectors_config=vectors_config)

        typer.echo(f"✅ Created '{collection}' collection.")

