import typer

app = typer.Typer(help="Orbit commands.")


def _log_candidates(candidates: list[str]):
    from sqlmodel import select

    from modules.mastodon.models import Status
    from shared.core.db import db_session

    print(candidates)

    with db_session() as db:
        statuses = db.exec(
            select(Status.language, Status.url).where(Status.id.in_(candidates))
        ).all()

        for status in statuses:
            typer.echo(status)


def _get_account_id_from_username(username: str):
    from sqlmodel import select

    from modules.mastodon.models import Account
    from shared.core.db import db_session

    with db_session() as db:
        account_id = db.scalar(select(Account.id).where(Account.username == username))

    if account_id is None:
        typer.echo(f"No account found with username '{username}'")

        raise typer.Exit(1)

    return account_id


@app.command("embedding")
def embedding(username: str):
    import numpy as np

    from shared.core.qdrant import client
    from shared.core.redis import get_redis

    entity = "consumers"
    account_id = _get_account_id_from_username(username)

    typer.echo(f"Account id of {username}: {account_id}")

    r = get_redis()
    version = r.get("orbit:version").decode("utf8")
    dim = int(r.get("orbit:dim").decode("utf8"))

    typer.echo(f"Orbit version hash: {version}")
    typer.echo(f"Orbit communities: {dim}")

    embedding = client.retrieve(
        collection_name=f"orbit_{version}_{entity}", ids=[account_id], with_vectors=True
    )[0].vector["embedding"]

    indices = np.array(embedding.indices)
    values = np.array(embedding.values)
    sorted_indices = np.argsort(values)[::-1]

    for i, v in zip(indices[sorted_indices], values[sorted_indices]):
        print(i, v)


@app.command("recommend")
def create_topics(community_id: int, limit: int = 10, entity: str = "statuses"):
    from qdrant_client import models
    from sqlmodel import select

    from modules.mastodon.models import Status, Tag
    from shared.core.db import db_session
    from shared.core.qdrant import client
    from shared.core.redis import get_redis

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
        with_vectors=True,
    )

    entity_ids = {rec.id for rec in recommendations}
    entities = {}
    with db_session() as db:
        if entity == "statuses":
            results = db.exec(select(Status).where(Status.id.in_(entity_ids))).fetchall()
            for result in results:
                entities[result.id] = result.local_url
        elif entity == "tags":
            results = db.exec(select(Tag.id, Tag.name).where(Tag.id.in_(entity_ids))).fetchall()
            for result in results:
                entities[result[0]] = result[1]

    for recommendation in recommendations:
        print(
            entities[recommendation.id],
            recommendation.score,
            recommendation.vector["embedding"],
        )


@app.command("compute-communities")
def compute_communities(
    path: str,
    min_tag_similarity: float = 0.3,
):
    from modules.orbit import (
        detect_communities,
        load_tag_similarities,
    )
    from shared.core.rw import rw_session

    with rw_session() as db:
        df = load_tag_similarities(db, min_tag_similarity)

    typer.echo(f"Computing communities for {len(df)} tag pairs.")

    communities = detect_communities(tag_similarities=df)

    community_tags = []
    for community in communities:
        community_tags.append(",".join([str(c) for c in community]))

    with open(path, "w") as f:
        f.writelines("\n".join(community_tags))
