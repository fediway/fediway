from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession
from sqlmodel import Session as RWSession

from apps.api.dependencies.auth import get_authenticated_account_or_fail
from apps.api.dependencies.feeds import get_feed_engine
from apps.api.feeds import SuggestionsFeed
from apps.api.services.feed_engine import FeedEngine
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import AccountItem
from modules.mastodon.models import Account
from shared.core.db import get_db_session
from shared.core.rw import get_rw_session

router = APIRouter()


@router.get("/suggestions")
async def follow_suggestions(
    request: Request,
    response: Response,
    offset: int = 0,
    engine: FeedEngine = Depends(get_feed_engine),
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
    db: DBSession = Depends(get_db_session),
):
    feed = SuggestionsFeed(account_id=account.id, rw=rw)

    results = await engine.run(
        feed,
        state_key=str(account.id),
        flush=(offset == 0),
        offset=offset,
        limit=config.fediway.feed_batch_size,
    )

    account_ids = [r.id for r in results]

    set_next_link(request, response, {"offset": offset + len(results)})

    accounts = db.exec(Account.select_by_ids(account_ids)).all()

    return [AccountItem.from_model(a) for a in accounts]
