import typer

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

    with db_session() as db:
        statuses = db.exec(select(Status).where(Status.id.in_(candidates))).all()

        for status in statuses:
            print(status.language, status.local_url)


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


@app.command("community-based-recommendations")
def community_based_recommendations(
    username: str,
    limit: int = 10,
):
    from modules.fediway.sources.statuses import CommunityBasedRecommendationsSource
    from shared.core.qdrant import client
    from shared.core.redis import get_redis

    account_id = _get_account_id_from_username(username)

    source = CommunityBasedRecommendationsSource(
        r=get_redis(), client=client, account_id=account_id
    )

    _log_candidates([c for c in source.collect(limit)])


@app.command("random-communities")
def random_communities(limit: int = 10, batch_size: int = 1):
    from modules.fediway.sources.statuses import TopStatusesFromRandomCommunitiesSource
    from shared.core.qdrant import client
    from shared.core.redis import get_redis

    source = TopStatusesFromRandomCommunitiesSource(
        r=get_redis(), client=client, batch_size=batch_size
    )

    _log_candidates([c for c in source.collect(limit)])


@app.command("viral")
def viral(
    limit: int = 10,
    language: str = "en",
):

    from modules.fediway.sources.statuses import ViralStatusesSource
    from shared.core.redis import get_redis
    from shared.core.rw import rw_session

    with rw_session() as rw:
        source = ViralStatusesSource(
            r=get_redis(),
            rw=rw,
            language=language,
        )

        source.reset()

        _log_candidates([c for c in source.collect(limit)])


@app.command("recent-statuses-by-followed-accounts")
def recent_statuses_by_followed_accounts(username: str, limit=10):
    from modules.fediway.sources.statuses import RecentStatusesByFollowedAccounts
    from shared.core.db import db_session

    account_id = _get_account_id_from_username(username)

    with db_session() as db:
        source = RecentStatusesByFollowedAccounts(
            db=db,
            account_id=account_id,
        )

        _log_candidates([c for c in source.collect(limit)])
