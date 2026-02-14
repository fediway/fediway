from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.services.feed_engine import FeedEngine, _generate_id, get_request_state_key


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "TestAgent/1.0"
    return request


@pytest.fixture
def mock_kafka():
    kafka = MagicMock()
    kafka.send.return_value = MagicMock()
    return kafka


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    redis.exists.return_value = False
    return redis


@pytest.fixture
def mock_tasks():
    return MagicMock()


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = 123
    return account


@pytest.fixture
def mock_feed():
    from modules.fediway.feed.candidates import CandidateList

    feed = MagicMock()
    feed.entity = "status_id"
    feed.__class__.__name__ = "TestFeed"
    feed.pipeline = MagicMock()
    feed.pipeline.counter = 1
    feed.pipeline.get_durations.return_value = [1000000, 2000000]

    candidates = CandidateList("status_id")
    candidates.append(1, score=0.9, source="s1", source_group="g1")
    candidates.append(2, score=0.8, source="s2", source_group="g2")
    feed.execute = AsyncMock(return_value=candidates)
    feed.flush = MagicMock()

    return feed


@pytest.fixture
def engine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account):
    return FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)


def test_generate_id():
    id1 = _generate_id()
    id2 = _generate_id()

    assert len(id1) == 8
    assert len(id2) == 8
    assert id1 != id2


def test_generate_id_custom_length():
    id1 = _generate_id(12)
    assert len(id1) == 12


def test_get_request_state_key():
    request = MagicMock()
    request.client.host = "192.168.1.1"
    request.headers.get.return_value = "Mozilla/5.0"

    key1 = get_request_state_key(request)

    assert len(key1) == 16
    assert key1.isalnum()


def test_get_request_state_key_same_request():
    request = MagicMock()
    request.client.host = "192.168.1.1"
    request.headers.get.return_value = "Mozilla/5.0"

    key1 = get_request_state_key(request)
    key2 = get_request_state_key(request)

    assert key1 == key2


def test_get_request_state_key_different_ip():
    request1 = MagicMock()
    request1.client.host = "192.168.1.1"
    request1.headers.get.return_value = "Mozilla/5.0"

    request2 = MagicMock()
    request2.client.host = "10.0.0.1"
    request2.headers.get.return_value = "Mozilla/5.0"

    key1 = get_request_state_key(request1)
    key2 = get_request_state_key(request2)

    assert key1 != key2


def test_get_request_state_key_none_client():
    request = MagicMock()
    request.client = None
    request.headers.get.return_value = "TestAgent"

    key = get_request_state_key(request)

    assert len(key) == 16


def test_engine_initialization(engine, mock_account):
    assert engine._account.id == 123
    assert len(engine._feed_id) == 8


def test_engine_session_id_creates_new(mock_kafka, mock_request, mock_tasks, mock_account):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    session = engine.get_session_id()

    assert len(session) == 12
    mock_redis.setex.assert_called_once()


def test_engine_session_id_returns_cached(mock_kafka, mock_request, mock_tasks, mock_account):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    session1 = engine.get_session_id()
    session2 = engine.get_session_id()

    assert session1 == session2
    # Only one Redis write (first call)
    assert mock_redis.setex.call_count == 1


def test_engine_session_id_loads_from_redis(mock_kafka, mock_request, mock_tasks, mock_account):
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"existing12ab"

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    session = engine.get_session_id()

    assert session == "existing12ab"
    mock_redis.expire.assert_called_once()  # TTL refresh
    mock_redis.setex.assert_not_called()  # No new session created


def test_engine_session_id_handles_redis_error(mock_kafka, mock_request, mock_tasks, mock_account):
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis error")

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)
    session = engine.get_session_id()

    # Should still return a valid session ID
    assert len(session) == 12


def test_engine_session_key_uses_account_id(mock_kafka, mock_redis, mock_request, mock_tasks):
    account = MagicMock()
    account.id = 456

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, account)
    key = engine._get_session_key()

    assert key == "feed_session:account:456"


def test_engine_session_key_uses_request_hash_for_guest(
    mock_kafka, mock_redis, mock_request, mock_tasks
):
    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, None)
    key = engine._get_session_key()

    assert key.startswith("feed_session:guest:")


def test_get_feed_state_key(engine, mock_feed):
    key = engine._get_feed_state_key(mock_feed, "user123")
    assert key == "feed:TestFeed:user123"


def test_load_feed_state_sets_state(engine, mock_feed, mock_redis):
    import json

    state = {"seen": [1, 2], "remembered": {"ids": []}, "heuristics": {}}
    mock_redis.get.return_value = json.dumps(state)

    engine._load_feed_state(mock_feed, "user123")

    mock_feed.set_state.assert_called_once_with(state)


def test_load_feed_state_handles_missing(engine, mock_feed, mock_redis):
    mock_redis.get.return_value = None

    engine._load_feed_state(mock_feed, "user123")

    mock_feed.set_state.assert_not_called()


def test_save_feed_state(engine, mock_feed, mock_redis):
    mock_feed.get_state.return_value = {"seen": [1], "remembered": {}, "heuristics": {}}

    engine._save_feed_state(mock_feed, "user123")

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "feed:TestFeed:user123"


def test_delete_feed_state(engine, mock_feed, mock_redis):
    engine._delete_feed_state(mock_feed, "user123")

    mock_redis.delete.assert_called_once_with("feed:TestFeed:user123")


@pytest.mark.asyncio
async def test_run_executes_feed(engine, mock_feed):
    mock_feed.get_state.return_value = {}

    results = await engine.run(mock_feed, state_key="user123")

    mock_feed.execute.assert_called_once()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_run_with_kwargs(engine, mock_feed):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123", max_id=100, limit=20)

    mock_feed.execute.assert_called_once_with(max_id=100, limit=20)


@pytest.mark.asyncio
async def test_run_loads_state(engine, mock_feed, mock_redis):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123")

    mock_redis.get.assert_called()


@pytest.mark.asyncio
async def test_run_saves_state(engine, mock_feed, mock_redis):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123")

    mock_redis.setex.assert_called()


@pytest.mark.asyncio
async def test_run_with_flush(engine, mock_feed, mock_redis):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123", flush=True)

    mock_feed.flush.assert_called_once()
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_run_without_flush(engine, mock_feed, mock_redis):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123", flush=False)

    mock_feed.flush.assert_not_called()


@pytest.mark.asyncio
async def test_run_adds_metrics_task(engine, mock_feed, mock_tasks):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123")

    assert mock_tasks.add_task.called


@pytest.mark.asyncio
async def test_run_with_prefetch(engine, mock_feed, mock_tasks):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123", prefetch=True)

    # Should add two tasks: metrics and prefetch
    assert mock_tasks.add_task.call_count == 2


@pytest.mark.asyncio
async def test_run_without_prefetch(engine, mock_feed, mock_tasks):
    mock_feed.get_state.return_value = {}

    await engine.run(mock_feed, state_key="user123", prefetch=False)

    # Should only add metrics task
    assert mock_tasks.add_task.call_count == 1


def test_emit_metrics_sends_kafka_messages(engine, mock_feed, mock_kafka):
    from modules.fediway.feed.candidates import CandidateList

    results = CandidateList("status_id")
    results.append(1, score=0.9, source="s1", source_group="g1")

    engine._emit_metrics(mock_feed, results)

    # Should send multiple messages: feed, pipeline_run, recommendations
    assert mock_kafka.send.call_count >= 3
    mock_kafka.flush.assert_called_once()


def test_emit_metrics_handles_errors(engine, mock_feed, mock_kafka):
    from modules.fediway.feed.candidates import CandidateList

    mock_kafka.send.side_effect = Exception("Kafka error")

    results = CandidateList("status_id")

    # Should not raise
    engine._emit_metrics(mock_feed, results)


@pytest.mark.asyncio
async def test_prefetch(engine, mock_feed, mock_redis):
    mock_feed.collect = AsyncMock()
    mock_feed.get_state.return_value = {}
    mock_feed._remembered = MagicMock()
    mock_feed._remembered.__len__ = MagicMock(return_value=100)

    await engine._prefetch(mock_feed, "user123")

    mock_feed.collect.assert_called_once()
    mock_redis.setex.assert_called()  # State saved after prefetch


@pytest.mark.asyncio
async def test_prefetch_handles_errors(engine, mock_feed):
    mock_feed.collect = AsyncMock(side_effect=Exception("Prefetch error"))

    # Should not raise
    await engine._prefetch(mock_feed, "user123")


@pytest.fixture
def engine_no_kafka(mock_redis, mock_request, mock_tasks, mock_account):
    return FeedEngine(None, mock_redis, mock_request, mock_tasks, mock_account)


def test_engine_initialization_with_no_kafka(engine_no_kafka):
    assert engine_no_kafka._kafka is None


@pytest.mark.asyncio
async def test_run_skips_metrics_when_kafka_is_none(engine_no_kafka, mock_feed, mock_tasks):
    mock_feed.get_state.return_value = {}

    results = await engine_no_kafka.run(mock_feed, state_key="user123")

    assert len(results) == 2
    # Only prefetch task, no metrics task
    metrics_calls = [
        c
        for c in mock_tasks.add_task.call_args_list
        if len(c[0]) >= 1 and c[0][0] == engine_no_kafka._emit_metrics
    ]
    assert len(metrics_calls) == 0


@pytest.mark.asyncio
async def test_run_still_prefetches_when_kafka_is_none(engine_no_kafka, mock_feed, mock_tasks):
    mock_feed.get_state.return_value = {}

    await engine_no_kafka.run(mock_feed, state_key="user123", prefetch=True)

    # Prefetch should still be scheduled
    assert mock_tasks.add_task.call_count == 1
