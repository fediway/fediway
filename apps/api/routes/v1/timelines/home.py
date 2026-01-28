from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session as DBSession

from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.statuses import (
    get_community_based_recommendations_source,
    # get_popular_in_social_circle_sources,
    get_recent_statuses_by_followed_accounts_source,
    get_top_statuses_from_random_communities_source,
    get_viral_statuses_source,
)
from apps.api.utils import set_next_link
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.feed.sampling import WeightedGroupSampler
from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session

router = APIRouter()


def get_in_network_sources(
    recent_statuses_by_followed_accounts: list[Source] = Depends(
        get_recent_statuses_by_followed_accounts_source
    ),
):
    return recent_statuses_by_followed_accounts


# def get_near_network_sources(
#     popular_in_social_circle: list[Source] = Depends(
#         get_popular_in_social_circle_sources
#     ),
# ):
#     return popular_in_social_circle


def get_out_network_sources(
    community_based_recommendations: list[Source] = Depends(
        get_community_based_recommendations_source
    ),
):
    return community_based_recommendations


def get_trending_sources(
    viral_statuses: list[Source] = Depends(get_viral_statuses_source),
):
    return viral_statuses


def get_cold_start_sources(
    top_statuses_from_random_communities: list[Source] = Depends(
        get_top_statuses_from_random_communities_source
    ),
):
    return top_statuses_from_random_communities


@router.get("/home")
async def home_timeline(
    request: Request,
    response: Response,
    max_id: int | None = None,
    feed: FeedService = Depends(get_feed),
    in_network_sources: list[Source] = Depends(get_in_network_sources),
    # near_network_sources: list[Source] = Depends(get_near_network_sources),
    out_network_sources: list[Source] = Depends(get_out_network_sources),
    trending_sources: list[Source] = Depends(get_trending_sources),
    cold_start_sources: list[Source] = Depends(get_cold_start_sources),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    max_candidates_per_source = config.fediway.max_candidates_per_source(
        len(in_network_sources)
        # len(near_network_sources) +
        + len(out_network_sources)
        + len(trending_sources)
        + len(cold_start_sources)
    )

    def _map_sources(S):
        return [(s, max_candidates_per_source) for s in S]

    pipeline = (
        feed.name("timelines/home")
        .select("status_id")
        .sources(_map_sources(in_network_sources), group="in-network")
        # .sources(_map_sources(near_network_sources), group="near-network")
        .sources(_map_sources(out_network_sources), group="out-network")
        .sources(_map_sources(trending_sources), group="trending")
        .sources(_map_sources(cold_start_sources), group="cold-start")
        .unique()
        .remember()
        .diversify(by="status:author_id", penalty=0.1)
        .sample(
            config.fediway.feed_batch_size,
            sampler=WeightedGroupSampler(
                {
                    "in-network": 0.5,
                    # "near-network": 0.25,
                    "out-network": 0.25,
                    "trending": 0.02,
                    "cold-start": 0.1,
                }
            ),
        )
        .paginate(config.fediway.feed_batch_size, max_id=max_id)
    )

    if max_id is None:
        feed.flush()

    recommendations = await pipeline.execute()
    status_ids = [r.id for r in recommendations]

    if len(status_ids) > 0:
        set_next_link(request, response, {"max_id": status_ids[-1]})

    statuses = db.exec(Status.select_by_ids(status_ids)).all()

    return [StatusItem.from_model(status) for status in statuses]
