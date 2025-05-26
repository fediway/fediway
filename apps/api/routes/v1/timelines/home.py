from fastapi import APIRouter, Depends, Request
from sqlmodel import Session as DBSession

from apps.api.core.ranker import kirby
from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.features import get_kirby_feature_service
from apps.api.dependencies.sources.statuses import (
    get_popular_by_influential_accounts_sources,
    get_newest_in_network_sources,
    get_collaborative_filtering_sources,
    get_popular_in_community_sources,
    get_popular_in_social_circle_sources,
    get_similar_to_favourited_sources,
)
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session


router = APIRouter()


def home_sources(
    popular_by_influential_accounts: list[Source] = Depends(
        get_popular_by_influential_accounts_sources
    ),
    newest_in_network: list[Source] = Depends(get_newest_in_network_sources),
    popular_in_community: list[Source] = Depends(get_popular_in_community_sources),
    popular_in_social_circle: list[Source] = Depends(
        get_popular_in_social_circle_sources
    ),
    collaborative_filtering: list[Source] = Depends(
        get_collaborative_filtering_sources
    ),
    similar_to_favourited: list[Source] = Depends(get_similar_to_favourited_sources),
):
    return (
        popular_by_influential_accounts
        + newest_in_network
        + popular_in_community
        + popular_in_social_circle
        + collaborative_filtering
        + similar_to_favourited
    )


@router.get("/home")
async def home_timeline(
    request: Request,
    feed: FeedService = Depends(get_feed),
    sources=Depends(home_sources),
    db: DBSession = Depends(get_db_session),
    kirby_features=Depends(get_kirby_feature_service),
) -> list[StatusItem]:
    max_candidates_per_source = config.fediway.max_candidates_per_source(len(sources))

    pipeline = (
        feed.name("timelines/home")
        .select("status_id")
        .sources([(source, max_candidates_per_source) for source in sources])
        .rank(kirby, kirby_features)
        .diversify(by="status:account_id", penalty=0.1)
        .sample(config.fediway.feed_batch_size)
        .paginate(config.fediway.feed_batch_size, offset=0)
    )

    recommendations = await feed.execute()

    statuses = db.exec(Status.select_by_ids(recommendations)).all()

    return [StatusItem.from_model(status) for status in statuses]
