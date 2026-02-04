from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_trending_config():
    config = MagicMock()
    config.settings = MagicMock()
    config.settings.window_hours = 24
    config.settings.max_per_author = 2
    config.settings.min_engagement = 5
    config.settings.local_only = False
    config.settings.batch_size = 20
    config.settings.diversity_penalty = 0.1
    return config


@pytest.fixture
def mock_algorithm_config(mock_trending_config):
    config = MagicMock()
    config.trends = MagicMock()
    config.trends.statuses = mock_trending_config
    return config


def test_trending_feed_instantiation(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed()

        assert feed.entity == "status_id"
        assert feed.languages == ["en"]


def test_trending_feed_with_languages(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed(languages=["en", "de", "es"])

        assert feed.languages == ["en", "de", "es"]


def test_trending_feed_get_min_candidates(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed()

        assert feed.get_min_candidates() == 5


@pytest.mark.asyncio
async def test_trending_feed_forward(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed()

        candidates = CandidateList("status_id")
        for i in range(50):
            candidates.append(i, score=1.0, source="viral", source_group="trending")

        result = await feed.forward(candidates)

        assert len(result) <= 20


@pytest.mark.asyncio
async def test_trending_feed_forward_unique(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed()

        candidates = CandidateList("status_id")
        candidates.append(1, source="viral", source_group="trending")
        candidates.append(1, source="viral2", source_group="trending")  # duplicate
        candidates.append(2, source="viral", source_group="trending")

        result = await feed.forward(candidates)

        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_trending_feed_forward_empty(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed()

        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


def test_trending_feed_is_feed_subclass(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed import Feed

        assert issubclass(TrendingStatusesFeed, Feed)


# Tests that require the actual sources module
try:
    from modules.fediway.sources.statuses import ViralStatusesSource  # noqa: F401

    HAS_SOURCES = True
except ImportError:
    HAS_SOURCES = False


@pytest.mark.skipif(not HAS_SOURCES, reason="Source dependencies not installed")
def test_trending_feed_sources_returns_dict(mock_algorithm_config):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        mock_redis = MagicMock()
        mock_rw = MagicMock()
        feed = TrendingStatusesFeed(redis=mock_redis, rw=mock_rw)

        sources = feed.sources()

        assert isinstance(sources, dict)
        assert "trending" in sources
        assert len(sources["trending"]) == 1  # One source per language
