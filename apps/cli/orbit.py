import typer

from config import config

app = typer.Typer(help="Orbit commands.")


@app.command("recommend")
def create_topics(community_id: int, limit: int = 10, entity: str = "statuses"):
    from modules.mastodon.models import Status, Tag, Account
    from shared.core.rw import rw_session
    from shared.core.redis import get_redis
    from shared.core.qdrant import client
    from qdrant_client import models
    from sqlmodel import select

    r = get_redis()

    version = r.get("orbit:version").decode("utf8")
    dim = int(r.get("orbit:dim").decode("utf8"))

    typer.echo(f"Orbit version hash: {version}")
    typer.echo(f"Orbit communities: {dim}")

    vector = models.SparseVector(indices=[community_id], values=[1.0])

    recommendations = client.search(
        collection_name=f"orbit_{version}_{entity}",
        query_vector=models.NamedSparseVector(name="embedding", vector=vector),
        limit=limit,
    )

    entity_ids = {rec.id for rec in recommendations}
    entities = {}
    with rw_session() as db:
        if entity == "statuses":
            results = db.exec(
                select(Status.id, Status.url).where(Status.id.in_(entity_ids))
            ).fetchall()
            for result in results:
                entities[result[0]] = result[1]
        elif entity == "tags":
            results = db.exec(
                select(Tag.id, Tag.name).where(Tag.id.in_(entity_ids))
            ).fetchall()
            for result in results:
                entities[result[0]] = result[1]

    for recommendation in recommendations:
        print(entities[recommendation.id], recommendation.score)
