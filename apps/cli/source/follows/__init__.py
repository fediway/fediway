import typer

from config import config

app = typer.Typer(help="Follow sources.")

@app.command("most-followed-by-follows")
def triangular_loop(account_id: int, limit: int = 10):
    from modules.fediway.sources.follows import MostFollowedByFollowsSource
    from shared.core.herde import db

    source = MostFollowedByFollowsSource(db, account_id)

    for account_id in source.collect(limit):
        print(account_id)


@app.command("triangular-loop")
def triangular_loop(account_id: int, limit: int = 10):
    from modules.fediway.sources.follows import TriangularLoopsSource
    from shared.core.herde import db

    source = TriangularLoopsSource(db, account_id)

    for account_id in source.collect(limit):
        print(account_id)


@app.command("recently-engaged")
def recently_engaged(
    account_id: int,
    limit: int = 10,
    max_age: int = config.fediway.follows_source_recently_engaged_age_in_days,
):
    from datetime import timedelta

    from modules.fediway.sources.follows import RecentlyEngagedSource
    from shared.core.herde import db

    source = RecentlyEngagedSource(db, account_id, timedelta(days=max_age))

    for account_id in source.collect(limit):
        print(account_id)


@app.command("recently-popular")
def recently_popular(account_id: int, lang: str = "en", limit: int = 10):
    from datetime import timedelta

    from modules.fediway.sources.follows import RecentlyPopularSource
    from shared.core.schwarm import driver

    source = RecentlyPopularSource(driver, account_id, language=lang)

    for account_id in source.collect(limit):
        print(account_id)
