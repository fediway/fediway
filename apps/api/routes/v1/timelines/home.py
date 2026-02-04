from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.auth import get_authenticated_account_or_fail
from apps.api.dependencies.feeds import get_feed_engine, get_home_feed
from apps.api.feeds import HomeFeed
from apps.api.services.feed_engine import FeedEngine
from apps.api.utils import set_next_link
from config import config
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Account, Status
from shared.core.db import get_db_session

router = APIRouter()


@router.get("/home")
async def home_timeline(
    request: Request,
    response: Response,
    max_id: int | None = None,
    engine: FeedEngine = Depends(get_feed_engine),
    feed: HomeFeed = Depends(get_home_feed),
    account: Account = Depends(get_authenticated_account_or_fail),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    results = await engine.run(
        feed,
        state_key=str(account.id),
        flush=(max_id is None),
        max_id=max_id,
        limit=config.fediway.feed_batch_size,
    )

    status_ids = [r.id for r in results]

    if len(status_ids) > 0:
        set_next_link(request, response, {"max_id": status_ids[-1]})

    statuses = db.exec(Status.select_by_ids(status_ids)).all()

    return [StatusItem.from_model(status) for status in statuses]
