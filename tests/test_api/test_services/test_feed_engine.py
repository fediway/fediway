from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.services.feed_engine import FeedEngine, _generate_feed_id


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

    # Mock execute to return CandidateList
    candidates = CandidateList("status_id")
    candidates.append(1, score=0.9, source="s1", source_group="g1")
    candidates.append(2, score=0.8, source="s2", source_group="g2")
    feed.execute = AsyncMock(return_value=candidates)
    feed.flush = MagicMock()

    return feed


@pytest.fixture
def engine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account):
    return FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, mock_account)


def test_generate_feed_id():
    id1 = _generate_feed_id()
    id2 = _generate_feed_id()

    assert len(id1) == 8
    assert len(id2) == 8
    assert id1 != id2


def test_engine_initialization(engine, mock_account):
    assert engine._account.id == 123
    assert len(engine._id) == 8


@pytest.mark.asyncio
async def test_run_executes_feed(engine, mock_feed):
    results = await engine.run(mock_feed)

    mock_feed.execute.assert_called_once()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_run_with_kwargs(engine, mock_feed):
    await engine.run(mock_feed, max_id=100, limit=20)

    mock_feed.execute.assert_called_once_with(max_id=100, limit=20)


@pytest.mark.asyncio
async def test_run_with_flush(engine, mock_feed):
    await engine.run(mock_feed, flush=True)

    mock_feed.flush.assert_called_once()


@pytest.mark.asyncio
async def test_run_without_flush(engine, mock_feed):
    await engine.run(mock_feed, flush=False)

    mock_feed.flush.assert_not_called()


@pytest.mark.asyncio
async def test_run_adds_metrics_task(engine, mock_feed, mock_tasks):
    await engine.run(mock_feed)

    # Should add background task for metrics
    assert mock_tasks.add_task.called


@pytest.mark.asyncio
async def test_run_with_prefetch(engine, mock_feed, mock_tasks):
    await engine.run(mock_feed, prefetch=True)

    # Should add two tasks: metrics and prefetch
    assert mock_tasks.add_task.call_count == 2


@pytest.mark.asyncio
async def test_run_without_prefetch(engine, mock_feed, mock_tasks):
    await engine.run(mock_feed, prefetch=False)

    # Should only add metrics task
    assert mock_tasks.add_task.call_count == 1


@pytest.mark.asyncio
async def test_run_with_cache_stores_results(engine, mock_feed, mock_redis):
    await engine.run(mock_feed, cache_ttl=300)

    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args
    assert args[0][1] == 300  # TTL


@pytest.mark.asyncio
async def test_run_cache_hit(engine, mock_feed, mock_redis):
    # Setup cache hit
    mock_redis.get.return_value = '{"ids": [10, 20], "scores": [1.0, 0.9], "sources": {}}'

    results = await engine.run(mock_feed, cache_ttl=300, flush=False)

    # Feed.execute should not be called on cache hit
    mock_feed.execute.assert_not_called()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_run_cache_miss(engine, mock_feed, mock_redis):
    mock_redis.get.return_value = None

    results = await engine.run(mock_feed, cache_ttl=300)

    mock_feed.execute.assert_called_once()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_run_flush_bypasses_cache(engine, mock_feed, mock_redis):
    # Setup cache
    mock_redis.get.return_value = '{"ids": [10], "scores": [1.0], "sources": {}}'

    await engine.run(mock_feed, cache_ttl=300, flush=True)

    # Should execute even with cache present
    mock_feed.execute.assert_called_once()


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
async def test_prefetch_next(engine, mock_feed):
    from modules.fediway.feed.candidates import CandidateList

    results = CandidateList("status_id")
    results.append(100, source="s1", source_group="g1")

    await engine._prefetch_next(mock_feed, results, limit=20)

    # Should call execute with max_id
    mock_feed.execute.assert_called_with(max_id=100, limit=20)


@pytest.mark.asyncio
async def test_prefetch_next_empty_results(engine, mock_feed):
    from modules.fediway.feed.candidates import CandidateList

    results = CandidateList("status_id")

    await engine._prefetch_next(mock_feed, results)

    # Should not call execute for empty results
    mock_feed.execute.assert_not_called()


def test_cache_key_includes_kwargs(engine, mock_feed):
    key1 = engine._cache_key(mock_feed, max_id=100, limit=20)
    key2 = engine._cache_key(mock_feed, max_id=200, limit=20)
    key3 = engine._cache_key(mock_feed, max_id=100, limit=20)

    assert key1 != key2
    assert key1 == key3
