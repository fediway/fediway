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