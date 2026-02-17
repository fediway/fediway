import typer
from sqlmodel import select

from modules.mastodon.models import Account
from shared.core.db import db_session

app = typer.Typer(help="Account sources.")


def _get_account_id_from_username(username: str):
    with db_session() as db:
        account_id = db.scalar(select(Account.id).where(Account.username == username))

    if account_id is None:
        typer.echo(f"No account found with username '{username}'")
        raise typer.Exit(1)

    return account_id


def _log_accounts(account_ids: list[int]):
    with db_session() as db:
        accounts = db.exec(select(Account).where(Account.id.in_(account_ids))).all()
        lines = [a.local_url for a in accounts]

    for url in lines:
        print(url)


@app.command("popular")
def popular(username: str, limit: int = 10):
    from apps.api.sources.accounts import PopularAccountsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = PopularAccountsSource(rw=rw, account_id=account_id)
        _log_accounts(source.collect(limit))


@app.command("similar-interests")
def similar_interests(username: str, limit: int = 10):
    from apps.api.sources.accounts import SimilarInterestsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = SimilarInterestsSource(rw=rw, account_id=account_id)
        _log_accounts(source.collect(limit))


@app.command("followed-by-friends")
def followed_by_friends(username: str, limit: int = 10):
    from apps.api.sources.accounts import FollowedByFriendsSource
    from shared.core.rw import rw_session

    account_id = _get_account_id_from_username(username)

    with rw_session() as rw:
        source = FollowedByFriendsSource(rw=rw, account_id=account_id)
        _log_accounts(source.collect(limit))
