from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.auth import get_authenticated_account_or_fail
from apps.api.dependencies.feeds import get_feed_engine, get_suggestions_feed
from apps.api.feeds import SuggestionsFeed
from apps.api.services.feed_engine import FeedEngine
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import AccountItem
from modules.mastodon.models import Account
from shared.core.db import get_db_session

router = APIRouter()


@router.get("/suggestions")
async def follow_suggestions(
    request: Request,
    response: Response,
    offset: int = 0,
    engine: FeedEngine = Depends(get_feed_engine),
    feed: SuggestionsFeed = Depends(get_suggestions_feed),
    account: Account = Depends(get_authenticated_account_or_fail),
    db: DBSession = Depends(get_db_session),
):
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

    # Preserve ranked order — database returns arbitrary order
    account_map = {a.id: a for a in accounts}
    accounts = [account_map[aid] for aid in account_ids if aid in account_map]

    return [AccountItem.from_model(a) for a in accounts]
