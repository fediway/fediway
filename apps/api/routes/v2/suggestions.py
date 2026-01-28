from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.follows import get_recently_popular_sources
from apps.api.modules.utils import set_next_link
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.sources import Source
from modules.mastodon.items import AccountItem
from modules.mastodon.models import Account
from shared.core.db import get_db_session

router = APIRouter()


def get_follow_suggestions_sources(
    recently_popular: list[Source] = Depends(get_recently_popular_sources),
):
    return recently_popular


@router.get("/suggestions")
async def follow_suggestions(
    request: Request,
    response: Response,
    feed: FeedService = Depends(get_feed),
    db: DBSession = Depends(get_db_session),
    sources: list[Source] = Depends(get_follow_suggestions_sources),
):
    max_candidates_per_source = 20

    (
        feed.name("v2/suggestions")
        .select("account_id")
        .sources([(source, max_candidates_per_source) for source in sources])
        .remember()
        .sample(config.fediway.feed_batch_size)
        .paginate(config.fediway.feed_batch_size, offset=0)
    )

    recommendations = await feed.execute()

    set_next_link(request, response, {"offset": len(recommendations)})

    accounts = db.exec(Account.select_by_ids(recommendations)).all()

    return [AccountItem.from_model(account) for account in accounts]
