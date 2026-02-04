from unittest.mock import MagicMock, patch

import pytest


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
    config.sources.smart_follows.enabled = True
    config.sources.follows_engaging.enabled = True
    config.sources.tag_affinity.enabled = True
    config.sources.second_degree.enabled = True
    config.sources.trending.enabled = True
    return config


@pytest.fixture
def mock_algorithm_config(mock_home_config):
    config = MagicMock()
    config.home = mock_home_config
    return config


def test_home_feed_instantiation(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123)

        assert feed.account_id == 123
        assert feed.entity == "status_id"
        assert feed.languages == ["en"]


def test_home_feed_with_languages(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, languages=["en", "de"])

        assert feed.languages == ["en", "de"]


def test_home_feed_state_key_from_account_id(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        mock_redis = MagicMock()
        feed = HomeFeed(account_id=456, redis=mock_redis)

        assert feed._state_key == "456"


def test_home_feed_get_min_candidates(mock_algorithm_config):
    mock_algorithm_config.home.settings.batch_size = 25

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123)

        assert feed.get_min_candidates() == 25


def test_home_feed_group_weights(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123)
        weights = feed._get_group_weights()

        assert weights["in-network"] == 0.5
        assert weights["discovery"] == 0.35
        assert weights["trending"] == 0.15
        assert weights["fallback"] == 0.1


def test_home_feed_group_weights_without_config_weights(mock_algorithm_config):
    mock_algorithm_config.home.weights = None

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123)
        weights = feed._get_group_weights()

        # Should use defaults
        assert weights["in-network"] == 0.5
        assert weights["discovery"] == 0.35
        assert weights["trending"] == 0.15


@pytest.mark.asyncio
async def test_home_feed_forward(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123)

        candidates = CandidateList("status_id")
        for i in range(50):
            candidates.append(i, score=1.0, source="test", source_group="in-network")

        result = await feed.forward(candidates)

        # Should sample down to batch_size
        assert len(result) <= 20


@pytest.mark.asyncio
async def test_home_feed_forward_unique(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123)

        candidates = CandidateList("status_id")
        # Add duplicates
        candidates.append(1, source="s1", source_group="in-network")
        candidates.append(1, source="s2", source_group="discovery")
        candidates.append(2, source="s1", source_group="in-network")

        result = await feed.forward(candidates)

        # Should have unique IDs only
        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_home_feed_forward_empty(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = HomeFeed(account_id=123)

        candidates = CandidateList("status_id")

        result = await feed.forward(candidates)

        assert len(result) == 0


def test_home_feed_is_feed_subclass(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed
        from modules.fediway.feed import Feed

        assert issubclass(HomeFeed, Feed)


# Tests that require the actual sources module (may skip if dependencies missing)
try:
    from modules.fediway.sources.statuses import SmartFollowsSource  # noqa: F401

    HAS_SOURCES = True
except ImportError:
    HAS_SOURCES = False


@pytest.mark.skipif(not HAS_SOURCES, reason="Source dependencies not installed")
def test_home_feed_sources_returns_dict(mock_algorithm_config):
    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        mock_rw = MagicMock()
        mock_redis = MagicMock()
        feed = HomeFeed(account_id=123, rw=mock_rw, redis=mock_redis)

        sources = feed.sources()

        assert isinstance(sources, dict)
        assert "in-network" in sources
        assert "discovery" in sources
        assert "trending" in sources
        assert "_fallback" in sources


@pytest.mark.skipif(not HAS_SOURCES, reason="Source dependencies not installed")
def test_home_feed_sources_respects_enabled_flags(mock_algorithm_config):
    mock_algorithm_config.home.sources.smart_follows.enabled = False
    mock_algorithm_config.home.sources.follows_engaging.enabled = False

    with patch("apps.api.feeds.home.algorithm_config", mock_algorithm_config):
        from apps.api.feeds.home import HomeFeed

        mock_rw = MagicMock()
        feed = HomeFeed(account_id=123, rw=mock_rw)

        sources = feed.sources()

        # In-network should be empty since both sources disabled
        assert sources["in-network"] == []
