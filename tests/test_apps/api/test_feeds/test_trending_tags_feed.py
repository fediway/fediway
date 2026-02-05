from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_trending_tags_config():
    config = MagicMock()
    config.settings = MagicMock()
    config.settings.window_hours = 24
    config.settings.min_posts = 3
    config.settings.min_accounts = 2
    config.settings.max_results = 20
    config.settings.local_only = False
    config.scoring = MagicMock()
    config.scoring.weight_posts = 1.0
    config.scoring.weight_accounts = 2.0
    config.scoring.velocity_boost = True
    config.filters = MagicMock()
    config.filters.blocked_tags = []
    return config


@pytest.fixture
def mock_algorithm_config(mock_trending_tags_config):
    config = MagicMock()
    config.trends = MagicMock()
    config.trends.tags = mock_trending_tags_config
    return config


@pytest.fixture
def mock_sources():
    return {"trending": []}


def test_trending_tags_feed_instantiation(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed

        feed = TrendingTagsFeed(sources=mock_sources)

        assert feed.entity == "tag_id"


def test_trending_tags_feed_get_min_candidates(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed

        feed = TrendingTagsFeed(sources=mock_sources)

        assert feed.get_min_candidates() == 5


def test_trending_tags_feed_sources_returns_injected_dict(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed

        feed = TrendingTagsFeed(sources=mock_sources)

        sources = feed.sources()

        assert sources is mock_sources
        assert isinstance(sources, dict)
        assert "trending" in sources


@pytest.mark.asyncio
async def test_trending_tags_feed_forward(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingTagsFeed(sources=mock_sources)

        candidates = CandidateList("tag_id")
        for i in range(50):
            candidates.append(i, score=1.0, source="trending", source_group="trending")

        result = await feed.forward(candidates)

        assert len(result) <= 20


@pytest.mark.asyncio
async def test_trending_tags_feed_forward_unique(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingTagsFeed(sources=mock_sources)

        candidates = CandidateList("tag_id")
        candidates.append(1, source="trending1", source_group="trending")
        candidates.append(1, source="trending2", source_group="trending")  # duplicate
        candidates.append(2, source="trending1", source_group="trending")

        result = await feed.forward(candidates)

        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_trending_tags_feed_forward_empty(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = TrendingTagsFeed(sources=mock_sources)

        candidates = CandidateList("tag_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


def test_trending_tags_feed_is_feed_subclass(mock_algorithm_config, mock_sources):
    with patch("apps.api.feeds.trending_tags.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.trending_tags import TrendingTagsFeed
        from modules.fediway.feed import Feed

        assert issubclass(TrendingTagsFeed, Feed)
