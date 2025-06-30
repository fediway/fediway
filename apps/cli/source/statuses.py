import typer

from config import config

app = typer.Typer(help="Follow sources.")


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


def _log_candidates(candidates: list[str]):
    from sqlmodel import select
    from modules.mastodon.models import Status
    from shared.core.db import db_session

    print(candidates)

    with db_session() as db:
        statuses = db.exec(select(Status.url).where(Status.id.in_(candidates))).all()

        for status in statuses:
            typer.echo(status)


@app.command("popular-in-social-circle")
def triangular_loop(account_id: int, limit: int = 10):
    from modules.fediway.sources.statuses import PopularInSocialCircleSource
    from shared.core.herde import db

    source = PopularInSocialCircleSource(db, account_id)

    for candidate in source.collect(limit):
        print(candidate)


@app.command("newest-in-network")
def triangular_loop(account_id: int, limit: int = 10):
    from modules.fediway.sources.statuses import NewestInNetworkSource
    from shared.core.herde import db

    source = NewestInNetworkSource(db, account_id)

    for candidate in source.collect(limit):
        print(candidate)


@app.command("community-recommendations")
def community_recommendations(
    username: str,
    limit: int = 10,
):
    from modules.fediway.sources.statuses import CommunityRecommendationsSource
    from shared.core.redis import get_redis
    from shared.core.qdrant import client

    account_id = _get_account_id_from_username(username)

    source = CommunityRecommendationsSource(
        r=get_redis(), client=client, account_id=account_id
    )

    _log_candidates([c for c in source.collect(limit)])


@app.command("random-communities")
def random_communities(limit: int = 10, batch_size: int = 1):
    from modules.fediway.sources.statuses import RandomCommunitiesSource
    from shared.core.redis import get_redis
    from shared.core.qdrant import client

    source = RandomCommunitiesSource(
        r=get_redis(), client=client, batch_size=batch_size
    )

    _log_candidates([c for c in source.collect(limit)])


@app.command("viral")
def viral(
    limit: int = 10,
    language: str = "en",
):
    from modules.fediway.sources.statuses import ViralSource
    from shared.core.rw import rw_session
    from shared.core.redis import get_redis
    import time

    with rw_session() as rw:
        source = ViralSource(
            r=get_redis(),
            rw=rw,
            language=language,
        )

        source.reset()

        for candidate in source.collect(limit):
            print(candidate)


@app.command("unusual-popularity")
def unusual_popularity(
    limit: int = 10,
    language: str = "en",
    decay_rate: float = 1.0,
    max_age_in_days: int = 3,
):
    from modules.fediway.sources.statuses import UnusualPopularitySource
    from shared.core.rw import rw_session
    from shared.core.redis import get_redis
    import time

    with rw_session() as rw:
        source = UnusualPopularitySource(
            r=get_redis(),
            rw=rw,
            language=language,
            decay_rate=decay_rate,
            max_age_in_days=max_age_in_days,
        )

        for candidate in source.collect(limit):
            print(candidate)
