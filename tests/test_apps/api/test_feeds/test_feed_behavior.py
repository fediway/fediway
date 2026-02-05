"""
Behavioral tests for feed implementations.

These tests verify that feeds actually apply weights, sampling, and diversification
correctly - not just that they return the right types.
"""

from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from modules.fediway.feed.candidates import CandidateList


@pytest.fixture
def mock_home_config():
    config = MagicMock()
    config.weights = MagicMock()
    config.weights.in_network = 50
    config.weights.discovery = 30
    config.weights.trending = 20
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
def mock_suggestions_config():
    config = MagicMock()
    config.weights = MagicMock()
    config.weights.social_proof = 50
    config.weights.similar_interests = 30
    config.weights.popular = 20
    config.settings = MagicMock()
    config.settings.max_results = 40
    config.settings.exclude_following = True
    config.settings.min_account_age_days = 7
    config.sources = MagicMock()
    config.sources.social_proof.enabled = True
    config.sources.social_proof.min_mutual_follows = 2
    config.sources.similar_interests.enabled = True
    config.sources.similar_interests.min_tag_overlap = 3
    config.sources.popular.enabled = True
    config.sources.popular.min_followers = 10
    config.sources.popular.local_only = True
    return config


@pytest.fixture
def mock_home_sources():
    return {
        "in-network": [],
        "discovery": [],
        "trending": [],
        "_fallback": [],
    }


@pytest.fixture
def mock_suggestions_sources():
    return {
        "social_proof": [],
        "similar": [],
        "popular": [],
    }


def _create_candidates_with_groups(
    entity: str, groups: dict[str, int], base_score: float = 1.0
) -> CandidateList:
    """Create candidates distributed across groups."""
    candidates = CandidateList(entity)
    id_counter = 1

    for group, count in groups.items():
        for _ in range(count):
            candidates.append(
                id_counter,
                score=base_score,
                source=f"source_{group}",
                source_group=group,
            )
            id_counter += 1

    return candidates


def _get_group_from_candidate(candidate) -> str | None:
    """Extract the group from a candidate's sources."""
    for _, group in candidate.sources:
        return group
    return None


@pytest.mark.asyncio
async def test_home_feed_forward_samples_according_to_weights(mock_home_config, mock_home_sources):
    """Verify that forward() samples candidates roughly according to configured weights."""
    mock_config = MagicMock()
    mock_config.feeds.timelines.home = mock_home_config

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_home_sources)

        candidates = _create_candidates_with_groups(
            "status_id",
            {"in-network": 100, "discovery": 100, "trending": 100},
        )

        results = await feed.forward(candidates)
        group_counts = Counter()
        for i in range(len(results)):
            group = _get_group_from_candidate(results[i])
            group_counts[group] += 1

        total = len(results)
        assert total == 20

        in_network_ratio = group_counts.get("in-network", 0) / total
        discovery_ratio = group_counts.get("discovery", 0) / total
        trending_ratio = group_counts.get("trending", 0) / total

        assert 0.3 <= in_network_ratio <= 0.7
        assert 0.1 <= discovery_ratio <= 0.5
        assert 0.05 <= trending_ratio <= 0.4


@pytest.mark.asyncio
async def test_home_feed_forward_removes_duplicates(mock_home_config, mock_home_sources):
    """Verify that forward() removes duplicate candidate IDs."""
    mock_config = MagicMock()
    mock_config.feeds.timelines.home = mock_home_config

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_home_sources)

        candidates = CandidateList("status_id")
        for i in range(10):
            candidates.append(i, source="s1", source_group="in-network")
            candidates.append(i, source="s2", source_group="discovery")
            candidates.append(i, source="s3", source_group="trending")

        results = await feed.forward(candidates)

        result_ids = [results[i].id for i in range(len(results))]
        assert len(result_ids) == len(set(result_ids))


@pytest.mark.asyncio
async def test_suggestions_feed_forward_samples_according_to_weights(
    mock_suggestions_config, mock_suggestions_sources
):
    """Verify that SuggestionsFeed samples according to configured weights."""
    mock_config = MagicMock()
    mock_config.feeds.suggestions = mock_suggestions_config

    with patch("apps.api.feeds.suggestions.config", mock_config):
        from apps.api.feeds.suggestions import SuggestionsFeed

        feed = SuggestionsFeed(account_id=123, sources=mock_suggestions_sources)

        candidates = _create_candidates_with_groups(
            "account_id",
            {"social_proof": 100, "similar": 100, "popular": 100},
        )

        results = await feed.forward(candidates)
        group_counts = Counter()
        for i in range(len(results)):
            group = _get_group_from_candidate(results[i])
            group_counts[group] += 1

        total = len(results)
        assert total == 40

        social_proof_ratio = group_counts.get("social_proof", 0) / total
        similar_ratio = group_counts.get("similar", 0) / total
        popular_ratio = group_counts.get("popular", 0) / total

        assert 0.3 <= social_proof_ratio <= 0.7
        assert 0.1 <= similar_ratio <= 0.5
        assert 0.05 <= popular_ratio <= 0.4


@pytest.mark.asyncio
async def test_feed_forward_handles_insufficient_candidates(mock_home_config, mock_home_sources):
    """Verify that forward() handles fewer candidates than batch_size."""
    mock_config = MagicMock()
    mock_config.feeds.timelines.home = mock_home_config
    mock_home_config.settings.batch_size = 50

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_home_sources)

        candidates = _create_candidates_with_groups(
            "status_id",
            {"in-network": 5, "discovery": 3, "trending": 2},
        )

        results = await feed.forward(candidates)

        assert len(results) == 10


@pytest.mark.asyncio
async def test_feed_forward_handles_single_group(mock_home_config, mock_home_sources):
    """Verify that forward() works when only one group has candidates."""
    mock_config = MagicMock()
    mock_config.feeds.timelines.home = mock_home_config

    with patch("apps.api.feeds.home.config", mock_config):
        from apps.api.feeds.home import HomeFeed

        feed = HomeFeed(account_id=123, sources=mock_home_sources)

        candidates = _create_candidates_with_groups(
            "status_id",
            {"in-network": 50, "discovery": 0, "trending": 0},
        )

        results = await feed.forward(candidates)

        assert len(results) == 20
        for i in range(len(results)):
            r = results[i]
            assert any(g == "in-network" for _, g in r.sources)
