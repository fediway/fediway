from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_home_config():
    home_config = MagicMock()
    home_config.weights = MagicMock()
    home_config.weights.in_network = 50
    home_config.weights.discovery = 35
    home_config.weights.trending = 15
    home_config.settings = MagicMock()
    home_config.settings.max_per_author = 3
    home_config.settings.diversity_penalty = 0.1
    home_config.settings.batch_size = 20
    home_config.sources = MagicMock()
    home_config.sources.top_follows.enabled = True
    home_config.sources.engaged_by_friends.enabled = True
    home_config.sources.tag_affinity.enabled = True
    home_config.sources.posted_by_friends_of_friends.enabled = True
    home_config.sources.trending.enabled = True
    return home_config


@pytest.fixture
def mock_config(mock_home_config):
    cfg = MagicMock()
    cfg.feeds.timelines.home = mock_home_config
    return cfg


@pytest.fixture
def mock_sources():
    return {
        "in-network": [],
        "discovery": [],
        "trending": [],
        "_fallback": [],
    }


def test_home_feed_instantiation(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)

        assert feed.account_id == 123
        assert feed.entity == "status_id"


def test_home_feed_get_min_candidates(mock_config, mock_sources):
    mock_config.feeds.timelines.home.settings.batch_size = 25

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)

        assert feed.get_min_candidates() == 25


def test_home_feed_group_weights(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)
        weights = feed._get_group_weights()

        assert weights["in-network"] == 0.5
        assert weights["discovery"] == 0.35
        assert weights["trending"] == 0.15
        assert weights["fallback"] == 0.1


def test_home_feed_group_weights_without_config_weights(mock_config, mock_sources):
    mock_config.feeds.timelines.home.weights = None

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)
        weights = feed._get_group_weights()

        # Should use defaults
        assert weights["in-network"] == 0.5
        assert weights["discovery"] == 0.35
        assert weights["trending"] == 0.15


@pytest.mark.asyncio
async def test_home_feed_forward(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("status_id")
        for i in range(50):
            candidates.append(i, score=1.0, source="test", source_group="in-network")

        result = await feed.forward(candidates)

        # Should sample down to batch_size
        assert len(result) <= 20


@pytest.mark.asyncio
async def test_home_feed_forward_unique(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("status_id")
        # Add duplicates
        candidates.append(1, source="s1", source_group="in-network")
        candidates.append(1, source="s2", source_group="discovery")
        candidates.append(2, source="s1", source_group="in-network")

        result = await feed.forward(candidates)

        # Should have unique IDs only
        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_home_feed_forward_empty(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


def test_home_feed_is_feed_subclass(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed import Feed

        assert issubclass(HomeFeed, Feed)


def test_home_feed_sources_returns_injected_dict(mock_config, mock_sources):
    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_sources)

        sources = feed.sources()

        assert sources is mock_sources
        assert isinstance(sources, dict)
        assert "in-network" in sources
        assert "discovery" in sources
        assert "trending" in sources
        assert "_fallback" in sources
