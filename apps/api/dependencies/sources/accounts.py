from fastapi import Depends
from sqlmodel import Session as RWSession

from apps.api.sources.accounts import (
    FollowedByFriendsSource,
    PopularAccountsSource,
    SimilarInterestsSource,
)
from config.algorithm import algorithm_config
from modules.fediway.sources import Source
from modules.mastodon.models import Account
from shared.core.rw import get_rw_session

from ..auth import get_authenticated_account_or_fail


def get_followed_by_friends_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.suggestions
    if not cfg.sources.followed_by_friends.enabled:
        return []
    return [
        (
            FollowedByFriendsSource(
                rw=rw,
                account_id=account.id,
                min_mutual_follows=cfg.sources.followed_by_friends.min_mutual_follows,
                exclude_following=cfg.settings.exclude_following,
            ),
            25,
        )
    ]


def get_similar_interests_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.suggestions
    if not cfg.sources.similar_interests.enabled:
        return []
    return [
        (
            SimilarInterestsSource(
                rw=rw,
                account_id=account.id,
                min_tag_overlap=cfg.sources.similar_interests.min_tag_overlap,
                exclude_following=cfg.settings.exclude_following,
            ),
            25,
        )
    ]


def get_popular_accounts_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.suggestions
    if not cfg.sources.popular.enabled:
        return []
    return [
        (
            PopularAccountsSource(
                rw=rw,
                account_id=account.id,
                min_followers=cfg.sources.popular.min_followers,
                local_only=cfg.sources.popular.local_only,
                exclude_following=cfg.settings.exclude_following,
                min_account_age_days=cfg.settings.min_account_age_days,
            ),
            25,
        )
    ]


# Group aggregators


def get_social_proof_sources(
    followed_by_friends: list[tuple[Source, int]] = Depends(get_followed_by_friends_source),
) -> list[tuple[Source, int]]:
    return followed_by_friends


def get_similar_sources(
    similar_interests: list[tuple[Source, int]] = Depends(get_similar_interests_source),
) -> list[tuple[Source, int]]:
    return similar_interests


def get_popular_sources(
    popular: list[tuple[Source, int]] = Depends(get_popular_accounts_source),
) -> list[tuple[Source, int]]:
    return popular


# Sources container


def get_suggestions_sources(
    social_proof: list[tuple[Source, int]] = Depends(get_social_proof_sources),
    similar: list[tuple[Source, int]] = Depends(get_similar_sources),
    popular: list[tuple[Source, int]] = Depends(get_popular_sources),
) -> dict[str, list[tuple[Source, int]]]:
    return {
        "social_proof": social_proof,
        "similar": similar,
        "popular": popular,
    }
