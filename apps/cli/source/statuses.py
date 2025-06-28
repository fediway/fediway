import typer

from config import config

app = typer.Typer(help="Follow sources.")


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


@app.command("orbit")
def viral(
    account_id: int,
    limit: int = 10,
):
    from modules.fediway.sources.statuses import OrbitSource
    from shared.core.redis import get_redis
    from shared.core.qdrant import client

    source = OrbitSource(r=get_redis(), client=client, account_id=account_id)

    for candidate in source.collect(limit):
        print(candidate)


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
