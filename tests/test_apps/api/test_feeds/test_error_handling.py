"""
Error handling tests for feed implementations.

These tests verify that feeds handle failures gracefully.
"""

from unittest.mock import MagicMock, patch

import pytest

from modules.fediway.feed.candidates import CandidateList
from modules.fediway.sources.base import Source


class FailingSource(Source):
    _tracked_params = []
    _id = "failing_source"

    def __init__(self, error_message="Source failed"):
        self.error_message = error_message

    def collect(self, limit: int):
        raise RuntimeError(self.error_message)


class WorkingSource(Source):
    _tracked_params = []
    _id = "working_source"

    def collect(self, limit: int):
        return list(range(1, limit + 1))


@pytest.fixture
def mock_home_config():
    config = MagicMock()
    config.weights = MagicMock()
    config.weights.in_network = 50
    config.weights.discovery = 35
    config.weights.trending = 15
    config.settings = MagicMock()
    config.settings.max_per_author = 3
    config.settings.diversity_penalty = 0.1
    config.settings.batch_size = 20
    config.sources = MagicMock()
    config.sources.top_follows.enabled = True
    config.sources.engaged_by_friends.enabled = True
    config.sources.tag_affinity.enabled = True
    config.sources.posted_by_friends_of_friends.enabled = True
    config.sources.trending.enabled = True
    return config


@pytest.fixture
def mock_sources():
    return {
        "in-network": [],
        "discovery": [],
        "trending": [],
        "_fallback": [],
    }


@pytest.mark.asyncio
async def test_feed_forward_returns_empty_on_empty_input(mock_home_config, mock_sources):
    """Verify forward() handles empty candidate list."""
    mock_algorithm_config = MagicMock()
    mock_algorithm_config.home = mock_home_config

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)
        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


@pytest.mark.asyncio
async def test_feed_forward_returns_candidates_not_none(mock_home_config, mock_sources):
    """Verify forward() always returns a CandidateList, never None."""
    mock_algorithm_config = MagicMock()
    mock_algorithm_config.home = mock_home_config

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)
        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert result is not None
        assert isinstance(result, CandidateList)


@pytest.mark.asyncio
async def test_feed_base_handles_source_failure_gracefully():
    """Verify that a failing source doesn't crash the entire feed."""
    from modules.fediway.feed import Feed

    class TestFeed(Feed):
        entity = "test_id"

        def __init__(self):
            super().__init__()
            self._failing_source = FailingSource()

        def sources(self):
            return {
                "failing": [(self._failing_source, 10)],
            }

        async def forward(self, candidates):
            return candidates

    feed = TestFeed()
    result = await feed.execute()

    assert result is not None
    assert len(result) == 0


@pytest.mark.asyncio
async def test_feed_continues_with_remaining_sources_on_partial_failure():
    """Verify that if one source fails, other sources still contribute."""
    from modules.fediway.feed import Feed

    class TestFeed(Feed):
        entity = "test_id"

        def __init__(self):
            super().__init__()

        def sources(self):
            return {
                "failing": [(FailingSource(), 10)],
                "working": [(WorkingSource(), 10)],
            }

        async def forward(self, candidates):
            return candidates

    feed = TestFeed()
    result = await feed.execute()

    assert len(result) == 10


@pytest.mark.asyncio
async def test_feed_engine_state_load_handles_invalid_json():
    """Verify that corrupted state in Redis doesn't crash the FeedEngine."""
    from apps.api.services.feed_engine import FeedEngine
    from modules.fediway.feed import Feed

    class TestFeed(Feed):
        entity = "test_id"

        def sources(self):
            return {"test": [(WorkingSource(), 10)]}

        async def forward(self, candidates):
            return candidates

    mock_redis = MagicMock()
    mock_redis.get.return_value = "not valid json {"
    mock_kafka = MagicMock()
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get.return_value = "Test"
    mock_tasks = MagicMock()

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, None)
    feed = TestFeed()

    result = await engine.run(feed, state_key="test_user")

    assert result is not None


@pytest.mark.asyncio
async def test_feed_engine_state_save_handles_redis_failure():
    """Verify that Redis failure on save doesn't crash the FeedEngine."""
    from apps.api.services.feed_engine import FeedEngine
    from modules.fediway.feed import Feed

    class TestFeed(Feed):
        entity = "test_id"

        def sources(self):
            return {"test": [(WorkingSource(), 10)]}

        async def forward(self, candidates):
            return candidates

    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.setex.side_effect = Exception("Redis connection lost")
    mock_kafka = MagicMock()
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get.return_value = "Test"
    mock_tasks = MagicMock()

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, None)
    feed = TestFeed()

    result = await engine.run(feed, state_key="test_user")

    assert result is not None


@pytest.mark.asyncio
async def test_feed_engine_flush_deletes_redis_state():
    """Verify that flush deletes Redis state via FeedEngine."""
    from apps.api.services.feed_engine import FeedEngine
    from modules.fediway.feed import Feed

    class TestFeed(Feed):
        entity = "test_id"

        def sources(self):
            return {"test": [(WorkingSource(), 10)]}

        async def forward(self, candidates):
            return candidates

    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_kafka = MagicMock()
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get.return_value = "Test"
    mock_tasks = MagicMock()

    engine = FeedEngine(mock_kafka, mock_redis, mock_request, mock_tasks, None)
    feed = TestFeed()

    await engine.run(feed, state_key="test_user", flush=True)

    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_feed_handles_none_weights_gracefully(mock_home_config, mock_sources):
    """Verify that feed works when weights config is None."""
    mock_home_config.weights = None
    mock_algorithm_config = MagicMock()
    mock_algorithm_config.home = mock_home_config

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("status_id")
        for i in range(30):
            candidates.append(i, source="test", source_group="in-network")

        result = await feed.forward(candidates)

        assert len(result) == 20
