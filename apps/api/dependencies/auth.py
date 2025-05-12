
from fastapi import Request, HTTPException, status

from modules.mastodon.models import Account

def get_authenticated_account_or_fail(request: Request) -> Account:
    account = None

    try:
        account = request.state.account
    except KeyError:
        pass
    
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return account