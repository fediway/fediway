import json
from unittest.mock import NonCallableMagicMock

from apps.api.utils.cache import redis_cache


def _make_redis_mock():
    """Create a non-callable mock that behaves like a Redis client."""
    return NonCallableMagicMock()


def test_returns_cached_value():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = b'{"result": "cached"}'

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_func(arg):
        return {"result": "fresh"}

    result = my_func("key1")

    assert result == {"result": "cached"}
    mock_redis.get.assert_called_with("test:key1")


def test_calls_function_on_cache_miss():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None

    call_count = 0

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_func(arg):
        nonlocal call_count
        call_count += 1
        return {"result": "fresh"}

    result = my_func("key1")

    assert result == {"result": "fresh"}
    assert call_count == 1
    mock_redis.setex.assert_called()


def test_stores_result_in_cache():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None

    @redis_cache(client=mock_redis, key="test:{0}", ttl=600)
    def my_func(arg):
        return {"data": [1, 2, 3]}

    my_func("mykey")

    mock_redis.setex.assert_called_with(
        "test:mykey", 600, json.dumps({"data": [1, 2, 3]})
    )


def test_default_ttl_is_300():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_func(arg):
        return {}

    my_func("key")

    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 300


def test_callable_client():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = b'"cached"'

    def get_redis():
        return mock_redis

    @redis_cache(client=get_redis, key="test:{0}")
    def my_func(arg):
        return "fresh"

    result = my_func("key")

    assert result == "cached"


def test_key_format_with_kwargs():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None

    @redis_cache(client=mock_redis, key="user:{user_id}:data")
    def my_func(user_id):
        return {}

    my_func(user_id=123)

    mock_redis.get.assert_called_with("user:123:data")


def test_key_format_with_multiple_args():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None

    @redis_cache(client=mock_redis, key="cache:{0}:{1}")
    def my_func(a, b):
        return {}

    my_func("first", "second")

    mock_redis.get.assert_called_with("cache:first:second")


def test_handles_redis_get_exception():
    mock_redis = _make_redis_mock()
    mock_redis.get.side_effect = Exception("Redis error")

    call_count = 0

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_func(arg):
        nonlocal call_count
        call_count += 1
        return "result"

    result = my_func("key")

    assert result == "result"
    assert call_count == 1


def test_handles_redis_setex_exception():
    mock_redis = _make_redis_mock()
    mock_redis.get.return_value = None
    mock_redis.setex.side_effect = Exception("Redis error")

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_func(arg):
        return "result"

    result = my_func("key")
    assert result == "result"


def test_preserves_function_metadata():
    mock_redis = _make_redis_mock()

    @redis_cache(client=mock_redis, key="test:{0}")
    def my_documented_func(arg):
        """My docstring."""
        return arg

    assert my_documented_func.__name__ == "my_documented_func"
    assert my_documented_func.__doc__ == "My docstring."
