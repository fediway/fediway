from datetime import timedelta

from fastapi import Depends

from config import config
from modules.fediway.sources import Source
from modules.fediway.sources.statuses import (
    CollaborativeFilteringSource,
    PopularInCommunitySource,
    PouplarByInfluentialAccountsSource,
    PopularInSocialCircleSource,
    SimilarToFavouritedSource,
)
from modules.mastodon.models import Account
from shared.core.qdrant import client as qdrant_client
from shared.core.schwarm import driver as schwarm_driver
from shared.core.herde import db as herde_db
from shared.services.feature_service import FeatureService

from ..auth import get_authenticated_account_or_fail
from ..features import get_feature_service
from ..lang import get_languages

MAX_AGE = timedelta(days=config.fediway.feed_max_age_in_days)


def get_popular_by_influential_accounts_sources(
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        PouplarByInfluentialAccountsSource(
            driver=schwarm_driver,
            language=lang,
            decay_rate=config.fediway.feed_decay_rate,
        )
        for lang in languages
    ]


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


def get_popular_in_social_circle_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        PopularInSocialCircleSource(
            db=herde_db,
            account_id=account.id,
            language=lang,
            max_age=MAX_AGE,
        )
        for lang in languages
    ]


def get_similar_to_favourited_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
    feature_service: FeatureService = Depends(get_feature_service),
) -> list[Source]:
    return [
        SimilarToFavouritedSource(
            client=qdrant_client,
            account_id=account.id,
            language=lang,
            feature_service=feature_service,
            max_age=MAX_AGE,
        )
        for lang in languages
    ]
