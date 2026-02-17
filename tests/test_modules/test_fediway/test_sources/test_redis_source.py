import json
from datetime import timedelta
from unittest.mock import MagicMock

from modules.fediway.sources.base import RedisSource


class StubRedisSource(RedisSource):
    _tracked_params: list[str] = []

    def compute(self):
        return [1, 2, 3]


def test_load_fetches_from_redis_when_exists():
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps([10, 20, 30])

    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))
    result = source.load()

    assert result == [10, 20, 30]
    mock_redis.setex.assert_not_called()


def test_load_returns_empty_when_not_exists():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))
    result = source.load()

    assert result == []
    mock_redis.setex.assert_not_called()


def test_load_handles_json_decode_error():
    mock_redis = MagicMock()
    mock_redis.get.return_value = "invalid json {"

    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))
    result = source.load()

    mock_redis.delete.assert_called_once()
    assert result == []


def test_load_handles_none_from_redis():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))
    result = source.load()

    assert result == []


def test_collect_limits_results():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps([1, 2, 3, 4, 5])

    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))
    result = source.collect(limit=2)

    assert result == [1, 2]


def test_redis_key_uses_source_id():
    mock_redis = MagicMock()
    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))

    assert source.redis_key() == "source:stub_redis_source"


def test_reset_deletes_key():
    mock_redis = MagicMock()
    source = StubRedisSource(r=mock_redis, ttl=timedelta(seconds=60))

    source.reset()

    mock_redis.delete.assert_called_once_with("source:stub_redis_source")
