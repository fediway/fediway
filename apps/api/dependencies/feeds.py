from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Depends, Request
from redis import Redis

from modules.fediway.sources import Source
from modules.mastodon.models import Account
from shared.core.kafka import get_kafka_producer
from shared.core.redis import get_redis

from ..services.feed_engine import FeedEngine
from .auth import get_authenticated_account, get_authenticated_account_or_fail
from .features import get_feature_service_optional
from .sources.accounts import get_suggestions_sources
from .sources.statuses import get_home_sources, get_trending_statuses_sources
from .sources.tags import get_trending_tags_sources

if TYPE_CHECKING:
    from kafka import KafkaProducer

    from ..feeds import HomeFeed, SuggestionsFeed, TrendingStatusesFeed, TrendingTagsFeed


def get_feed_engine(
    request: Request,
    tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    kafka: "KafkaProducer | None" = Depends(get_kafka_producer),
    account: Account | None = Depends(get_authenticated_account),
) -> FeedEngine:
    return FeedEngine(
        kafka=kafka,
        redis=redis,
        request=request,
        tasks=tasks,
        account=account,
    )


def get_home_feed(
    account: Account = Depends(get_authenticated_account_or_fail),
    sources: dict[str, list[tuple[Source, int]]] = Depends(get_home_sources),
    feature_service=Depends(get_feature_service_optional),
) -> "HomeFeed":
    from ..feeds import HomeFeed

    return HomeFeed(
        account_id=account.id,
        sources=sources,
        feature_service=feature_service,
    )


def get_suggestions_feed(
    account: Account = Depends(get_authenticated_account_or_fail),
    sources: dict[str, list[tuple[Source, int]]] = Depends(get_suggestions_sources),
) -> "SuggestionsFeed":
    from ..feeds import SuggestionsFeed

    return SuggestionsFeed(account_id=account.id, sources=sources)


def get_trending_statuses_feed(
    sources: dict[str, list[tuple[Source, int]]] = Depends(get_trending_statuses_sources),
) -> "TrendingStatusesFeed":
    from ..feeds import TrendingStatusesFeed

    return TrendingStatusesFeed(sources=sources)


def get_trending_tags_feed(
    sources: dict[str, list[tuple[Source, int]]] = Depends(get_trending_tags_sources),
) -> "TrendingTagsFeed":
    from ..feeds import TrendingTagsFeed

    return TrendingTagsFeed(sources=sources)
