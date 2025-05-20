from fastapi import APIRouter, Depends
from sqlmodel import select, Session as DBSession

from modules.mastodon.items import AccountItem
from modules.mastodon.models import Account
from modules.fediway.sources import Source

from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.follows import get_recently_popular_sources
from apps.api.services.feed_service import FeedService

from shared.core.db import get_db_session

router = APIRouter()


def follow_suggestions_sources(
    recently_popular: list[Source] = Depends(get_recently_popular_sources),
):
    return recently_popular


@router.get("/suggestions")
async def follow_suggestions(
    feed: FeedService = Depends(get_feed),
    db: DBSession = Depends(get_db_session),
):
    max_candidates_per_source = 20

    pipeline = (
        feed.name("v2/suggestions")
        .select("account_id")
        .sources([(source, max_candidates_per_source) for source in sources])
        .remember()
        .sample(config.fediway.feed_batch_size)
        .paginate(config.fediway.feed_batch_size, offset=offset)
    )

    recommendations = await feed.execute()

    accounts = db.exec(Account.select_by_ids(recommendations)).all()

    return [AccountItem.from_model(account) for account in accounts]
