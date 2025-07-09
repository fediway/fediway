from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks
from sqlmodel import Session as DBSession

from apps.api.modules.utils import set_next_link
from apps.api.dependencies.features import get_kirby_feature_service
from apps.api.dependencies.feeds import get_feed
from apps.api.dependencies.sources.statuses import (
    # get_popular_in_social_circle_sources,
    get_community_based_recommendations_source,
    get_top_statuses_from_random_communities_source,
    get_viral_statuses_source,
)
from apps.api.services.feed_service import FeedService
from config import config
from modules.fediway.rankers.kirby import KirbyFeatureService
from modules.fediway.feed import CandidateList
from modules.fediway.feed.sampling import WeightedGroupSampler
from modules.fediway.sources import Source
from modules.mastodon.items import StatusItem
from modules.mastodon.models import Status
from shared.core.db import get_db_session


router = APIRouter()


# def get_in_network_sources(
#     newest_in_network: list[Source] = Depends(get_newest_in_network_sources),
# ):
#     return newest_in_network


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
    background_tasks: BackgroundTasks,
    max_id: int | None = None,
    feed: FeedService = Depends(get_feed),
    # in_network_sources: list[Source] = Depends(get_in_network_sources),
    # near_network_sources: list[Source] = Depends(get_near_network_sources),
    out_network_sources: list[Source] = Depends(get_out_network_sources),
    trending_sources: list[Source] = Depends(get_trending_sources),
    cold_start_sources: list[Source] = Depends(get_cold_start_sources),
    kirby_features: KirbyFeatureService = Depends(get_kirby_feature_service),
    db: DBSession = Depends(get_db_session),
) -> list[StatusItem]:
    async def _push_kirby_features_to_offline_store(candidates: CandidateList):
        background_tasks.add_task(kirby_features.get, candidates.get_entity_rows())
        return candidates

    max_candidates_per_source = config.fediway.max_candidates_per_source(
        # len(in_network_sources) +
        # len(near_network_sources) +
        len(out_network_sources) + len(trending_sources) + len(cold_start_sources)
    )

    _map_sources = lambda S: [(s, max_candidates_per_source) for s in S]

    pipeline = (
        feed.name("timelines/home")
        .select("status_id")
        # .sources(_map_sources(in_network_sources), group="in-network")
        # .sources(_map_sources(near_network_sources), group="near-network")
        .sources(_map_sources(out_network_sources), group="out-network")
        .sources(_map_sources(trending_sources), group="trending")
        .sources(_map_sources(cold_start_sources), group="cold-start")
        .unique()
        .passthrough(_push_kirby_features_to_offline_store)
        .remember()
        .diversify(by="status:author_id", penalty=0.1)
        .sample(
            config.fediway.feed_batch_size,
            sampler=WeightedGroupSampler(
                {
                    # "in-network": 0.5,
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
