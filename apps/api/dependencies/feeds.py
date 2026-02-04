from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Depends, Request
from redis import Redis

from modules.mastodon.models import Account
from shared.core.kafka import get_kafka_producer
from shared.core.redis import get_redis

from ..services.feed_service import FeedService
from .auth import get_authenticated_account
from .features import get_feature_service

if TYPE_CHECKING:
    from kafka import KafkaProducer

    from shared.services.feature_service import FeatureService


def get_feed(
    request: Request,
    tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    kafka: "KafkaProducer" = Depends(get_kafka_producer),
    feature_service: "FeatureService" = Depends(get_feature_service),
    account: Account | None = Depends(get_authenticated_account),
) -> FeedService:
    return FeedService(
        kafka=kafka,
        request=request,
        tasks=tasks,
        redis=redis,
        feature_service=feature_service,
        account=account,
    )
