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


@pytest.fixture
def mock_sources():
    return {"trending": []}


def test_trending_feed_instantiation(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed(sources=mock_sources)

        assert feed.entity == "status_id"


def test_trending_feed_get_min_candidates(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed(sources=mock_sources)

        assert feed.get_min_candidates() == 5


def test_trending_feed_sources_returns_injected_dict(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed

        feed = TrendingStatusesFeed(sources=mock_sources)

        sources = feed.sources()

        assert sources is mock_sources
        assert isinstance(sources, dict)
        assert "trending" in sources


@pytest.mark.asyncio
async def test_trending_feed_forward(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed(sources=mock_sources)

        candidates = CandidateList("status_id")
        for i in range(50):
            candidates.append(i, score=1.0, source="trending", source_group="trending")

        result = await feed.forward(candidates)

        assert len(result) <= 20


@pytest.mark.asyncio
async def test_trending_feed_forward_unique(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed(sources=mock_sources)

        candidates = CandidateList("status_id")
        candidates.append(1, source="trending", source_group="trending")
        candidates.append(1, source="viral2", source_group="trending")  # duplicate
        candidates.append(2, source="trending", source_group="trending")

        result = await feed.forward(candidates)

        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_trending_feed_forward_empty(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingStatusesFeed(sources=mock_sources)

        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


def test_trending_feed_is_feed_subclass(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_statuses.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_statuses import TrendingStatusesFeed
        from modules.fediway.feed import Feed

        assert issubclass(TrendingStatusesFeed, Feed)
