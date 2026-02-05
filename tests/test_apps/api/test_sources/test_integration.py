from unittest.mock import MagicMock

from apps.api.sources.statuses import (
    EngagedByFriendsSource,
    EngagedBySimilarUsersSource,
    PostedByFriendsOfFriendsSource,
    TagAffinitySource,
    TopFollowsSource,
)


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


def _import_sources_config():
    import importlib.util

    spec = importlib.util.spec_from_file_location("config.sources", "config/sources.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SourcesConfig


SourcesConfig = _import_sources_config()


def test_source_weights_sum_to_one():
    cfg = SourcesConfig()

    total = (
        cfg.top_follows.weight
        + cfg.engaged_by_friends.weight
        + cfg.tag_affinity.weight
        + cfg.posted_by_friends_of_friends.weight
        + cfg.engaged_by_similar_users.weight
        + cfg.trending.weight
    )

    assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"


def test_source_weights_match_plan():
    cfg = SourcesConfig()

    assert cfg.top_follows.weight == 0.35
    assert cfg.engaged_by_friends.weight == 0.15
    assert cfg.tag_affinity.weight == 0.15
    assert cfg.posted_by_friends_of_friends.weight == 0.10
    assert cfg.engaged_by_similar_users.weight == 0.15
    assert cfg.trending.weight == 0.10


def test_all_mvp_sources_enabled_by_default():
    cfg = SourcesConfig()

    assert cfg.top_follows.enabled
    assert cfg.engaged_by_friends.enabled
    assert cfg.tag_affinity.enabled
    assert cfg.posted_by_friends_of_friends.enabled
    assert cfg.engaged_by_similar_users.enabled
    assert cfg.trending.enabled


def test_sources_config_get_enabled_returns_dict():
    cfg = SourcesConfig()
    enabled = cfg.get_enabled_sources()

    assert isinstance(enabled, dict)
    assert "top_follows" in enabled
    assert "trending" in enabled


def test_sources_config_group_weights():
    cfg = SourcesConfig()
    weights = cfg.get_group_weights()

    # in-network: top_follows (0.35) + engaged_by_friends (0.15) = 0.5
    assert abs(weights.get("in-network", 0) - 0.5) < 0.01

    # discovery: tag_affinity (0.15) + posted_by_friends_of_friends (0.1) + engaged_by_similar_users (0.15) = 0.4
    assert abs(weights.get("discovery", 0) - 0.4) < 0.01

    # trending: 0.1
    assert abs(weights.get("trending", 0) - 0.1) < 0.01


def test_home_sources_includes_fallback_group():
    """Verify get_home_sources includes fallback group for WeightedGroupSampler."""
    with open("apps/api/dependencies/sources/statuses.py") as f:
        content = f.read()
        assert '"_fallback"' in content, "Home sources should include _fallback group"
