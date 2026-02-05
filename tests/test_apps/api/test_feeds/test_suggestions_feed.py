from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_suggestions_config():
    suggestions_config = MagicMock()
    suggestions_config.settings = MagicMock()
    suggestions_config.settings.max_results = 40
    suggestions_config.settings.exclude_following = True
    suggestions_config.settings.min_account_age_days = 7
    suggestions_config.weights = MagicMock()
    suggestions_config.weights.social_proof = 40
    suggestions_config.weights.similar_interests = 35
    suggestions_config.weights.popular = 25
    suggestions_config.sources = MagicMock()
    suggestions_config.sources.social_proof.enabled = True
    suggestions_config.sources.social_proof.min_mutual_follows = 2
    suggestions_config.sources.similar_interests.enabled = True
    suggestions_config.sources.similar_interests.min_tag_overlap = 3
    suggestions_config.sources.popular.enabled = True
    suggestions_config.sources.popular.local_only = True
    suggestions_config.sources.popular.min_followers = 10
    return suggestions_config


@pytest.fixture
def mock_config(mock_suggestions_config):
    cfg = MagicMock()
    cfg.feeds.suggestions = mock_suggestions_config
    return cfg


@pytest.fixture
def mock_sources():
    return {
        "social_proof": [],
        "similar": [],
        "popular": [],
    }


def test_suggestions_feed_instantiation(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)

        assert feed.account_id == 123
        assert feed.entity == "account_id"


def test_suggestions_feed_get_min_candidates(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)

        assert feed.get_min_candidates() == 5


def test_suggestions_feed_group_weights(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)
        weights = feed._get_group_weights()

        assert weights["social_proof"] == 0.4
        assert weights["similar"] == 0.35
        assert weights["popular"] == 0.25


def test_suggestions_feed_group_weights_without_config(mock_config, mock_sources):
    mock_config.suggestions.weights = None

    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)
        weights = feed._get_group_weights()

        # Should use defaults
        assert weights["social_proof"] == 0.4
        assert weights["similar"] == 0.35
        assert weights["popular"] == 0.25


def test_suggestions_feed_sources_returns_injected_dict(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)
        sources = feed.sources()

        assert sources is mock_sources
        assert isinstance(sources, dict)
        assert "social_proof" in sources
        assert "similar" in sources
        assert "popular" in sources


@pytest.mark.asyncio
async def test_suggestions_feed_process(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("account_id")
        for i in range(100):
            candidates.append(i, score=1.0, source="test", source_group="social_proof")

        result = await feed.process(candidates)

        assert len(result) <= 40


@pytest.mark.asyncio
async def test_suggestions_feed_process_unique(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("account_id")
        candidates.append(1, source="s1", source_group="social_proof")
        candidates.append(1, source="s2", source_group="similar")  # duplicate
        candidates.append(2, source="s1", source_group="social_proof")

        result = await feed.process(candidates)

        assert len(set(result.get_candidates())) == len(result)


@pytest.mark.asyncio
async def test_suggestions_feed_process_empty(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed
        from modules.fediway.feed.candidates import CandidateList

        feed = SuggestionsFeed(account_id=123, sources=mock_sources)

        candidates = CandidateList("account_id")

        result = await feed.process(candidates)

        assert len(result) == 0


def test_suggestions_feed_is_feed_subclass(mock_config, mock_sources):
    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed
        from modules.fediway.feed import Feed

        assert issubclass(SuggestionsFeed, Feed)
