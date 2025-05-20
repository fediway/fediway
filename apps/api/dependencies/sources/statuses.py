
from fastapi import Depends
from datetime import timedelta

from modules.mastodon.models import Account
from modules.fediway.sources import Source
from modules.fediway.sources.statuses import (
    CollaborativeFilteringSource,
    PouplarStatusesByInfluentialAccountsSource,
    SimilarToFavourited,
    PopularInCommunitySource
)

from shared.services.feature_service import FeatureService
from shared.core.qdrant import client as qdrant_client
from shared.core.schwarm import driver as schwarm_driver
from config import config

from ..features import get_feature_service
from ..auth import get_authenticated_account_or_fail
from ..lang import get_languages

MAX_AGE = timedelta(days=config.fediway.feed_max_age_in_days)

def get_popular_by_influential_accounts_sources(
    languages: list[str] = Depends(get_languages)
) -> list[Source]:
    return [PouplarStatusesByInfluentialAccountsSource(
        driver=schwarm_driver, 
        language=lang,
        max_age=MAX_AGE,
        alpha=config.fediway.feed_decay_rate,
    ) for lang in languages]

def get_collaborative_filtering_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [CollaborativeFilteringSource(
        driver=schwarm_driver,
        account_id=account.id,
        language=lang, 
        max_age=MAX_AGE,
    ) for lang in languages]

def get_popular_in_community_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    return [PopularInCommunitySource(
        driver=schwarm_driver,
        account_id=account.id,
        language=lang, 
        max_age=MAX_AGE,
    )]

def get_similar_to_favourited_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
    feature_service: FeatureService = Depends(get_feature_service)
) -> list[Source]:
    return [SimilarToFavourited(
        client=qdrant_client,
        account_id=account.id,
        language=lang, 
        feature_service=feature_service,
        max_age=MAX_AGE,
    ) for lang in languages]