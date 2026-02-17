import typer

app = typer.Typer(help="Status sources.")


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
    from sqlalchemy.orm import selectinload
    from sqlmodel import select

    from modules.mastodon.models import Status
    from shared.core.db import db_session

    with db_session() as db:
        statuses = db.exec(
            select(Status).options(selectinload(Status.account)).where(Status.id.in_(candidates))
        ).all()
        lines = [(s.language, s.local_url) for s in statuses]

    for language, url in lines:
        print(language, url)


@app.command("trending")
def trending(
    limit: int = 10,
    language: str = "en",
):
    from apps.api.sources.statuses import TrendingStatusesSource
    from shared.core.redis import get_redis
    from shared.core.rw import rw_session

    with rw_session() as rw:
        source = TrendingStatusesSource(
            r=get_redis(),
            rw=rw,
            language=language,
        )

        source.reset()
        source.store()

        _log_candidates([c for c in source.collect(limit)])


@app.command("top-follows")
def top_follows(username: str, limit: int = 10):
    from apps.api.sources.statuses import TopFollowsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = TopFollowsSource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("engaged-by-similar-users")
def engaged_by_similar_users(username: str, limit: int = 10):
    from apps.api.sources.statuses import EngagedBySimilarUsersSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = EngagedBySimilarUsersSource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("popular-posts")
def popular_posts(username: str, limit: int = 10):
    from apps.api.sources.statuses import PopularPostsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = PopularPostsSource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("engaged-by-friends")
def engaged_by_friends(username: str, limit: int = 10):
    from apps.api.sources.statuses import EngagedByFriendsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = EngagedByFriendsSource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("tag-affinity")
def tag_affinity(username: str, limit: int = 10):
    from apps.api.sources.statuses import TagAffinitySource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = TagAffinitySource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("posted-by-friends-of-friends")
def posted_by_friends_of_friends(username: str, limit: int = 10):
    from apps.api.sources.statuses import PostedByFriendsOfFriendsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = PostedByFriendsOfFriendsSource(rw=rw, account_id=account_id)
        _log_candidates(source.collect(limit))


@app.command("community-based-recommendations")
def community_based_recommendations(
    username: str,
    limit: int = 10,
):
    from apps.api.sources.statuses import CommunityBasedRecommendationsSource
    from shared.core.qdrant import client
    from shared.core.redis import get_redis

    account_id = _get_account_id_from_username(username)

    source = CommunityBasedRecommendationsSource(
        r=get_redis(), client=client, account_id=account_id
    )

    _log_candidates([c for c in source.collect(limit)])


@app.command("random-communities")
def random_communities(limit: int = 10, batch_size: int = 1):
    from apps.api.sources.statuses import TopStatusesFromRandomCommunitiesSource
    from shared.core.qdrant import client
    from shared.core.redis import get_redis

    source = TopStatusesFromRandomCommunitiesSource(
        r=get_redis(), client=client, batch_size=batch_size
    )

    _log_candidates([c for c in source.collect(limit)])
