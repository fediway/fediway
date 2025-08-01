from datetime import timedelta
from sqlmodel import Session as DBSession
from fastapi import Depends
from redis import Redis

from config import config
from shared.core.redis import get_redis
from modules.fediway.sources import Source
from modules.fediway.sources.statuses import (
    AccountBasedCollaborativeFilteringSource,
    CollaborativeFilteringSource,
    NewestInNetworkSource,
    CommunityBasedRecommendationsSource,
    TopStatusesFromRandomCommunitiesSource,
    PopularInCommunitySource,
    PouplarByInfluentialAccountsSource,
    PopularInSocialCircleSource,
    RecentStatusesByFollowedAccounts,
    SimilarToEngagedSource,
    StatusBasedCollaborativeFilteringSource,
    ViralStatusesSource,
)
from modules.mastodon.models import Account
from shared.core.qdrant import client as qdrant_client
from shared.core.schwarm import driver as schwarm_driver

# from shared.core.herde import db as herde_db
from shared.services.feature_service import FeatureService
from shared.core.db import get_db_session
from shared.core.rw import get_rw_session

from ..auth import get_authenticated_account_or_fail
from ..features import get_feature_service
from ..lang import get_languages

MAX_AGE = timedelta(days=config.fediway.feed_max_age_in_days)


def get_recent_statuses_by_followed_accounts_source(
    db: DBSession = Depends(get_db_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    return [RecentStatusesByFollowedAccounts(db=db, account_id=account.id)]


def get_popular_by_influential_accounts_sources(
    r: Redis = Depends(get_redis),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        PouplarByInfluentialAccountsSource(
            r=r,
            driver=schwarm_driver,
            language=lang,
            decay_rate=config.fediway.feed_decay_rate,
            ttl=timedelta(minutes=10),
        )
        for lang in languages
    ]


def get_viral_statuses_source(
    r: Redis = Depends(get_redis),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        ViralStatusesSource(
            r=r,
            language=lang,
            ttl=timedelta(minutes=10),
        )
        for lang in languages
    ]


def get_community_based_recommendations_source(
    r: Redis = Depends(get_redis),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    return [
        CommunityBasedRecommendationsSource(
            r=r, client=qdrant_client, account_id=account.id
        )
    ]


def get_top_statuses_from_random_communities_source(
    r: Redis = Depends(get_redis),
) -> list[Source]:
    return [
        TopStatusesFromRandomCommunitiesSource(r=r, client=qdrant_client, batch_size=5)
    ]


# def get_newest_in_network_sources(
#     account: Account = Depends(get_authenticated_account_or_fail),
# ) -> list[Source]:
#     if herde_db is None:
#         return []

#     return [
#         NewestInNetworkSource(
#             db=herde_db,
#             account_id=account.id,
#         )
#     ]


def get_collaborative_filtering_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        CollaborativeFilteringSource(
            driver=schwarm_driver,
            account_id=account.id,
            language=lang,
        )
        for lang in languages
    ]


def get_popular_in_community_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    return [
        PopularInCommunitySource(
            driver=schwarm_driver,
            account_id=account.id,
            decay_rate=config.fediway.feed_decay_rate,
        )
    ]


# def get_account_based_collaborative_filtering_source(
#     r: Redis = Depends(get_redis),
#     account: Account = Depends(get_authenticated_account_or_fail),
# ) -> list[Source]:
#     if herde_db is None:
#         return []

#     return [
#         AccountBasedCollaborativeFilteringSource(
#             r=r,
#             account_id=account.id,
#         )
#     ]


# def get_status_based_collaborative_filtering_source(
#     r: Redis = Depends(get_redis),
#     account: Account = Depends(get_authenticated_account_or_fail),
# ) -> list[Source]:
#     if herde_db is None:
#         return []

#     return [
#         StatusBasedCollaborativeFilteringSource(
#             r=r,
#             account_id=account.id,
#         )
#     ]


# def get_popular_in_social_circle_sources(
#     account: Account = Depends(get_authenticated_account_or_fail),
#     languages: list[str] = Depends(get_languages),
# ) -> list[Source]:
#     if herde_db is None:
#         return []

#     return [
#         PopularInSocialCircleSource(
#             db=herde_db,
#             account_id=account.id,
#             language=lang,
#             max_age=MAX_AGE,
#         )
#         for lang in languages
#     ]


def get_similar_to_engaged_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
    feature_service: FeatureService = Depends(get_feature_service),
) -> list[Source]:
    return [
        SimilarToEngagedSource(
            client=qdrant_client,
            account_id=account.id,
            language=lang,
            feature_service=feature_service,
            max_age=MAX_AGE,
        )
        for lang in languages
    ]
