from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, Depends, Request
from redis import Redis

from modules.mastodon.models import Account
from shared.core.kafka import get_kafka_producer
from shared.core.redis import get_redis

from ..services.feed_engine import FeedEngine
from .auth import get_authenticated_account

if TYPE_CHECKING:
    from kafka import KafkaProducer


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
