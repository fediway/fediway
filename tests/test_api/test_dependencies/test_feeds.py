from unittest.mock import MagicMock

from apps.api.dependencies.feeds import get_feed_engine
from apps.api.services.feed_engine import FeedEngine


def test_get_feed_engine_returns_feed_engine():
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "TestAgent/1.0"
    tasks = MagicMock()
    redis = MagicMock()
    kafka = MagicMock()
    account = MagicMock()
    account.id = 123

    result = get_feed_engine(
        request=request,
        tasks=tasks,
        redis=redis,
        kafka=kafka,
        account=account,
    )

    assert isinstance(result, FeedEngine)


def test_get_feed_engine_without_account():
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "TestAgent/1.0"
    tasks = MagicMock()
    redis = MagicMock()
    kafka = MagicMock()

    result = get_feed_engine(
        request=request,
        tasks=tasks,
        redis=redis,
        kafka=kafka,
        account=None,
    )

    assert isinstance(result, FeedEngine)
