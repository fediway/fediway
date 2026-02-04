import typer

from config import config

app = typer.Typer(help="Qdrant commands.")

COLLECTIONS = [
    "status_embeddings",
    "latest_account_favourites_embeddings",
    "latest_account_reblogs_embeddings",
    "latest_account_replies_embeddings",
]


@app.command("migrate")
def migrate():
    from qdrant_client import models

    from shared.core.embed import embedder
    from shared.core.qdrant import client

    for collection in COLLECTIONS:
        if client.collection_exists(collection):
            continue

        vectors_config = models.VectorParams(size=embedder.dim(), distance=models.Distance.COSINE)
        client.create_collection(collection_name=collection, vectors_config=vectors_config)

        typer.echo(f"✅ Created '{collection}' collection.")


@app.command("purge")
def purge():
    from shared.core.qdrant import client

    for collection in COLLECTIONS:
        if not client.collection_exists(collection):
            continue

        client.delete_collection(collection_name=collection)

        typer.echo(f"✅ Deleted '{collection}' collection.")


@app.command("create-embeddings")
def create_embeddings(batch_size: int = 16):
    from qdrant_client.http import models
    from sqlmodel import func, select
    from tqdm import tqdm

    from modules.mastodon.models import Status
    from shared.core.db import db_session
    from shared.core.embed import embedder
    from shared.core.qdrant import client

    with db_session() as db:
        query_select = select(Status.id, Status.text, Status.created_at).where(
            Status.created_at > config.fediway.feed_max_age()
        )
        query_count = select(func.count(Status.id)).where(
            Status.created_at > config.fediway.feed_max_age()
        )

        bar = tqdm(desc="Statuses", total=db.scalar(query_count))

        batch = []
        for status in db.exec(query_select).mappings().yield_per(100):
            if client.retrieve(collection_name="status_embeddings", ids=[status["id"]]):
                bar.update(1)
                continue
            batch.append(status)
            if len(batch) >= batch_size:
                embeddings = embedder([s["text"] for s in batch])
                client.upsert(
                    collection_name="status_embeddings",
                    points=models.Batch(
                        ids=[status["id"] for status in batch],
                        vectors=embeddings,
                        payloads=[
                            {"created_at": status["created_at"].timestamp()} for status in batch
                        ],
                    ),
                )
                bar.update(len(batch))
                batch = []
        bar.exit()


@app.command("collect")
def collect(language: str = "en"):
    from datetime import timedelta

    from modules.fediway.sources.qdrant import SimilarToFavourited

    from shared.core.qdrant import client
    from shared.services.feature_service import FeatureService
    from shared.utils.logging import Timer, log_debug

    # source = MostInteractedByAccountsSource(
    #     driver=get_driver(),
    #     account_ids=[114397974544358424, 114397974544358424]
    #     # account_id=114394115240930061,
    #     # language='en',
    #     # max_age=timedelta(days=14)
    # )

    source = SimilarToFavourited(
        client=client,
        language=language,
        account_id=114398075274349836,
        feature_service=FeatureService(),
        max_age=timedelta(days=28),
    )

    # source = TrendingStatusesByTagsInCommunity(
    #     driver=get_driver(),
    #     account_id=114398075274349836
    # )

    with Timer() as t:
        for status_id in source.collect(10):
            continue
    log_debug("Collected candidates", module="qdrant", duration_ms=round(t.elapsed_ms, 2))

    with Timer() as t:
        for status_id in source.collect(10):
            print(status_id)
    log_debug("Collected candidates", module="qdrant", duration_ms=round(t.elapsed_ms, 2))
