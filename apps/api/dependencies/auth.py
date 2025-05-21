from fastapi import HTTPException, Request, status

from modules.mastodon.models import Account


def get_authenticated_account(request: Request) -> Account | None:
    account = None

    try:
        account = request.state.account
    except KeyError:
        pass

    return account


def get_authenticated_account_or_fail(request: Request) -> Account:
    account = get_authenticated_account(request)

    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return account
