from unittest.mock import MagicMock

from apps.api.sources.statuses import (
    EngagedByFriendsSource,
    EngagedBySimilarUsersSource,
    PostedByFriendsOfFriendsSource,
    TagAffinitySource,
    TopFollowsSource,
)
from config.feeds import load


def test_sources_have_unique_ids():
    mock_rw = MagicMock()

    top = TopFollowsSource(rw=mock_rw, account_id=1)
    engaged = EngagedByFriendsSource(rw=mock_rw, account_id=1)
    tag = TagAffinitySource(rw=mock_rw, account_id=1)
    posted = PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1)
    similar = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)

    ids = [top.id, engaged.id, tag.id, posted.id, similar.id]
    assert len(ids) == len(set(ids)), "Source IDs must be unique"


def test_all_sources_have_tracked_params():
    mock_rw = MagicMock()

    sources = [
        TopFollowsSource(rw=mock_rw, account_id=1),
        EngagedByFriendsSource(rw=mock_rw, account_id=1),
        TagAffinitySource(rw=mock_rw, account_id=1),
        PostedByFriendsOfFriendsSource(rw=mock_rw, account_id=1),
        EngagedBySimilarUsersSource(rw=mock_rw, account_id=1),
    ]

    for source in sources:
        params = source.get_params()
        assert isinstance(params, dict), f"{source.id} should return dict from get_params()"


def test_feeds_config_weights_sum_to_100():
    cfg = load()
    home = cfg.timelines.home

    total = home.weights.in_network + home.weights.discovery + home.weights.trending
    assert total == 100, f"Home weights should sum to 100, got {total}"


def test_feeds_config_default_weights():
    cfg = load()
    home = cfg.timelines.home

    assert home.weights.in_network == 50
    assert home.weights.discovery == 35
    assert home.weights.trending == 15


def test_home_sources_includes_fallback_group():
    """Verify get_home_sources includes fallback group for WeightedGroupSampler."""
    with open("apps/api/dependencies/sources/statuses.py") as f:
        content = f.read()
        assert '"_fallback"' in content, "Home sources should include _fallback group"
