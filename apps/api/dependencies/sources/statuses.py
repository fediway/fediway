from fastapi import Depends
from redis import Redis
from sqlmodel import Session as RWSession

from config.algorithm import algorithm_config
from modules.fediway.sources import Source
from modules.fediway.sources.statuses import (
    EngagedByFriendsSource,
    PostedByFriendsOfFriendsSource,
    TagAffinitySource,
    TopFollowsSource,
    TrendingStatusesSource,
)
from modules.mastodon.models import Account
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session

from ..auth import get_authenticated_account_or_fail
from ..lang import get_languages

# Home feed source dependencies


def get_home_top_follows_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.home
    if not cfg.sources.top_follows.enabled:
        return []
    return [
        (
            TopFollowsSource(
                rw=rw,
                account_id=account.id,
                max_per_author=cfg.settings.max_per_author,
            ),
            50,
        )
    ]


def get_home_engaged_by_friends_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.home
    if not cfg.sources.engaged_by_friends.enabled:
        return []
    return [
        (
            EngagedByFriendsSource(
                rw=rw,
                account_id=account.id,
            ),
            50,
        )
    ]


def get_home_tag_affinity_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.home
    if not cfg.sources.tag_affinity.enabled:
        return []
    return [
        (
            TagAffinitySource(
                rw=rw,
                account_id=account.id,
            ),
            50,
        )
    ]


def get_home_posted_by_friends_of_friends_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.home
    if not cfg.sources.posted_by_friends_of_friends.enabled:
        return []
    return [
        (
            PostedByFriendsOfFriendsSource(
                rw=rw,
                account_id=account.id,
            ),
            50,
        )
    ]


def get_home_trending_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
    languages: list[str] = Depends(get_languages),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.home
    if not cfg.sources.trending.enabled:
        return []
    return [
        (
            TrendingStatusesSource(
                r=r,
                rw=rw,
                language=lang,
            ),
            50,
        )
        for lang in languages
    ]


def get_home_fallback_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
    languages: list[str] = Depends(get_languages),
) -> list[tuple[Source, int]]:
    return [
        (
            TrendingStatusesSource(
                r=r,
                rw=rw,
                language=lang,
                top_n=200,
            ),
            25,
        )
        for lang in languages
    ]


# Group aggregators


def get_home_in_network_sources(
    top_follows: list[tuple[Source, int]] = Depends(get_home_top_follows_source),
    engaged_by_friends: list[tuple[Source, int]] = Depends(get_home_engaged_by_friends_source),
) -> list[tuple[Source, int]]:
    return top_follows + engaged_by_friends


def get_home_discovery_sources(
    tag_affinity: list[tuple[Source, int]] = Depends(get_home_tag_affinity_source),
    posted_by_friends_of_friends: list[tuple[Source, int]] = Depends(
        get_home_posted_by_friends_of_friends_source
    ),
) -> list[tuple[Source, int]]:
    return tag_affinity + posted_by_friends_of_friends


def get_home_trending_sources(
    trending: list[tuple[Source, int]] = Depends(get_home_trending_source),
) -> list[tuple[Source, int]]:
    return trending


def get_home_fallback_sources(
    fallback: list[tuple[Source, int]] = Depends(get_home_fallback_source),
) -> list[tuple[Source, int]]:
    return fallback


# Sources container


def get_home_sources(
    in_network: list[tuple[Source, int]] = Depends(get_home_in_network_sources),
    discovery: list[tuple[Source, int]] = Depends(get_home_discovery_sources),
    trending: list[tuple[Source, int]] = Depends(get_home_trending_sources),
    fallback: list[tuple[Source, int]] = Depends(get_home_fallback_sources),
) -> dict[str, list[tuple[Source, int]]]:
    return {
        "in-network": in_network,
        "discovery": discovery,
        "trending": trending,
        "_fallback": fallback,
    }


# Trending statuses feed sources


def get_trending_statuses_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
    languages: list[str] = Depends(get_languages),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.trends.statuses
    return [
        (
            TrendingStatusesSource(
                r=r,
                rw=rw,
                language=lang,
                top_n=200,
                max_per_author=cfg.settings.max_per_author,
            ),
            50,
        )
        for lang in languages
    ]


def get_trending_statuses_sources(
    trending: list[tuple[Source, int]] = Depends(get_trending_statuses_source),
) -> dict[str, list[tuple[Source, int]]]:
    return {"trending": trending}
