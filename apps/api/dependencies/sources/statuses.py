from datetime import timedelta

from fastapi import Depends
from redis import Redis
from sqlmodel import Session as DBSession
from sqlmodel import Session as RWSession

from config import config
from modules.fediway.sources import Source
from modules.fediway.sources.statuses import (
    AccountBasedCollaborativeFilteringSource,
    CollaborativeFilteringFallbackSource,
    CollaborativeFilteringSource,
    CommunityBasedRecommendationsSource,
    FollowsEngagingNowSource,
    RecentStatusesByFollowedAccounts,
    SecondDegreeSource,
    SimilarToEngagedSource,
    SmartFollowsSource,
    StatusBasedCollaborativeFilteringSource,
    TagAffinitySource,
    TopStatusesFromRandomCommunitiesSource,
    ViralStatusesSource,
)
from modules.mastodon.models import Account
from shared.core.db import get_db_session
from shared.core.qdrant import client as qdrant_client
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session
from shared.services.feature_service import FeatureService

from ..auth import get_authenticated_account_or_fail
from ..features import get_feature_service
from ..lang import get_languages

MAX_AGE = timedelta(days=config.fediway.feed_max_age_in_days)


def get_recent_statuses_by_followed_accounts_source(
    db: DBSession = Depends(get_db_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    return [RecentStatusesByFollowedAccounts(db=db, account_id=account.id)]


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
    if not config.fediway.orbit_enabled:
        return []
    return [CommunityBasedRecommendationsSource(r=r, client=qdrant_client, account_id=account.id)]


def get_top_statuses_from_random_communities_source(
    r: Redis = Depends(get_redis),
) -> list[Source]:
    if not config.fediway.orbit_enabled:
        return []
    return [TopStatusesFromRandomCommunitiesSource(r=r, client=qdrant_client, batch_size=5)]


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


def get_collaborative_filtering_sources(
    r: Redis = Depends(get_redis),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> list[Source]:
    if not config.fediway.collaborative_filtering_enabled:
        return []
    return [
        AccountBasedCollaborativeFilteringSource(r=r, account_id=account.id),
        StatusBasedCollaborativeFilteringSource(r=r, account_id=account.id),
    ]


# MVP Sources - Phase 6 Integration


def get_smart_follows_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> Source | None:
    if not config.fediway.is_source_enabled("smart_follows"):
        return None
    cfg = config.fediway.sources.smart_follows
    return SmartFollowsSource(
        rw=rw,
        account_id=account.id,
        recency_half_life_hours=cfg.params.get("recency_half_life_hours", 12),
        max_age_hours=cfg.params.get("post_window_hours", 48),
        max_per_author=cfg.params.get("max_per_author", 3),
        volume_threshold=cfg.params.get("volume_penalty_threshold", 5),
    )


def get_follows_engaging_now_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> Source | None:
    if not config.fediway.is_source_enabled("follows_engaging_now"):
        return None
    cfg = config.fediway.sources.follows_engaging_now
    return FollowsEngagingNowSource(
        rw=rw,
        account_id=account.id,
        min_engaged_follows=cfg.params.get("min_engagers", 2),
    )


def get_tag_affinity_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> Source | None:
    if not config.fediway.is_source_enabled("tag_affinity"):
        return None
    cfg = config.fediway.sources.tag_affinity
    return TagAffinitySource(
        rw=rw,
        account_id=account.id,
        max_age_hours=cfg.params.get("post_window_hours", 48),
        in_network_penalty=cfg.params.get("in_network_penalty", 0.5),
    )


def get_second_degree_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> Source | None:
    if not config.fediway.is_source_enabled("second_degree"):
        return None
    cfg = config.fediway.sources.second_degree
    return SecondDegreeSource(
        rw=rw,
        account_id=account.id,
        min_mutual_follows=cfg.params.get("min_mutual_follows", 2),
    )


def get_collaborative_filtering_mvp_source(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> Source | None:
    if not config.fediway.is_source_enabled("collaborative_filtering"):
        return None
    cfg = config.fediway.sources.collaborative_filtering
    return CollaborativeFilteringSource(
        rw=rw,
        account_id=account.id,
        max_per_author=cfg.params.get("max_per_author", 2),
    ).fallback(CollaborativeFilteringFallbackSource(rw=rw))


def get_trending_mvp_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    if not config.fediway.is_source_enabled("trending"):
        return []
    cfg = config.fediway.sources.trending
    return [
        ViralStatusesSource(
            r=r,
            rw=rw,
            language=lang,
            top_n=cfg.params.get("top_n", 200),
            max_per_author=cfg.params.get("max_per_author", 2),
        )
        for lang in languages
    ]


def get_trending_fallback_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    """Trending source for pipeline-level fallback (always enabled)."""
    return [
        ViralStatusesSource(
            r=r,
            rw=rw,
            language=lang,
            top_n=200,
            max_per_author=2,
        )
        for lang in languages
    ]


class MVPSources:
    """Container for all MVP sources with their configured weights."""

    def __init__(
        self,
        smart_follows: Source | None,
        follows_engaging_now: Source | None,
        tag_affinity: Source | None,
        second_degree: Source | None,
        collaborative_filtering: Source | None,
        trending: list[Source],
        trending_fallback: list[Source],
    ):
        self.smart_follows = smart_follows
        self.follows_engaging_now = follows_engaging_now
        self.tag_affinity = tag_affinity
        self.second_degree = second_degree
        self.collaborative_filtering = collaborative_filtering
        self.trending = trending
        self.trending_fallback = trending_fallback
        self._cfg = config.fediway.sources

    def get_in_network_sources(self) -> list[tuple[Source, float]]:
        """Returns (source, weight) tuples for in-network sources."""
        sources = []
        if self.smart_follows:
            sources.append((self.smart_follows, self._cfg.smart_follows.weight))
        if self.follows_engaging_now:
            sources.append((self.follows_engaging_now, self._cfg.follows_engaging_now.weight))
        return sources

    def get_discovery_sources(self) -> list[tuple[Source, float]]:
        """Returns (source, weight) tuples for discovery sources."""
        sources = []
        if self.tag_affinity:
            sources.append((self.tag_affinity, self._cfg.tag_affinity.weight))
        if self.second_degree:
            sources.append((self.second_degree, self._cfg.second_degree.weight))
        if self.collaborative_filtering:
            sources.append((self.collaborative_filtering, self._cfg.collaborative_filtering.weight))
        return sources

    def get_trending_sources(self) -> list[tuple[Source, float]]:
        """Returns (source, weight) tuples for trending sources."""
        weight_per = self._cfg.trending.weight / max(len(self.trending), 1)
        return [(s, weight_per) for s in self.trending]

    def get_all_sources_with_weights(self) -> dict[str, list[tuple[Source, float]]]:
        """Returns all sources grouped by category."""
        return {
            "in-network": self.get_in_network_sources(),
            "discovery": self.get_discovery_sources(),
            "trending": self.get_trending_sources(),
        }

    def get_group_weights(self) -> dict[str, float]:
        """Returns total weight per group for WeightedGroupSampler."""
        weights = {
            "in-network": sum(w for _, w in self.get_in_network_sources()),
            "discovery": sum(w for _, w in self.get_discovery_sources()),
            "trending": sum(w for _, w in self.get_trending_sources()),
        }
        # Include fallback group with small weight (used when main sources are empty)
        weights["fallback"] = 0.1
        return weights


def get_mvp_sources(
    smart_follows: Source | None = Depends(get_smart_follows_source),
    follows_engaging_now: Source | None = Depends(get_follows_engaging_now_source),
    tag_affinity: Source | None = Depends(get_tag_affinity_source),
    second_degree: Source | None = Depends(get_second_degree_source),
    collaborative_filtering: Source | None = Depends(get_collaborative_filtering_mvp_source),
    trending: list[Source] = Depends(get_trending_mvp_source),
    trending_fallback: list[Source] = Depends(get_trending_fallback_source),
) -> MVPSources:
    """Aggregated dependency that provides all MVP sources."""
    return MVPSources(
        smart_follows=smart_follows,
        follows_engaging_now=follows_engaging_now,
        tag_affinity=tag_affinity,
        second_degree=second_degree,
        collaborative_filtering=collaborative_filtering,
        trending=trending,
        trending_fallback=trending_fallback,
    )
