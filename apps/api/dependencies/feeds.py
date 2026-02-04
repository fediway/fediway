from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Depends, Request
from redis import Redis
from sqlmodel import Session as RWSession

from modules.mastodon.models import Account
from shared.core.kafka import get_kafka_producer
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session

from ..services.feed_engine import FeedEngine
from .auth import get_authenticated_account, get_authenticated_account_or_fail
from .features import get_feature_service_optional
from .lang import get_languages

if TYPE_CHECKING:
    from kafka import KafkaProducer

    from ..feeds import HomeFeed, SuggestionsFeed, TrendingStatusesFeed, TrendingTagsFeed


def get_feed_engine(
    request: Request,
    tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    kafka: "KafkaProducer" = Depends(get_kafka_producer),
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
    rw: RWSession = Depends(get_rw_session),
    redis: Redis = Depends(get_redis),
    languages: list[str] = Depends(get_languages),
    account: Account = Depends(get_authenticated_account_or_fail),
    feature_service=Depends(get_feature_service_optional),
) -> "HomeFeed":
    from ..feeds import HomeFeed

    return HomeFeed(
        account_id=account.id,
        rw=rw,
        redis=redis,
        feature_service=feature_service,
        languages=languages,
    )


def get_suggestions_feed(
    rw: RWSession = Depends(get_rw_session),
    account: Account = Depends(get_authenticated_account_or_fail),
) -> "SuggestionsFeed":
    from ..feeds import SuggestionsFeed

    return SuggestionsFeed(account_id=account.id, rw=rw)


def get_trending_statuses_feed(
    rw: RWSession = Depends(get_rw_session),
    redis: Redis = Depends(get_redis),
    languages: list[str] = Depends(get_languages),
) -> "TrendingStatusesFeed":
    from ..feeds import TrendingStatusesFeed

    return TrendingStatusesFeed(redis=redis, rw=rw, languages=languages)


def get_trending_tags_feed(
    rw: RWSession = Depends(get_rw_session),
    redis: Redis = Depends(get_redis),
) -> "TrendingTagsFeed":
    from ..feeds import TrendingTagsFeed

    return TrendingTagsFeed(redis=redis, rw=rw)
