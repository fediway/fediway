import sys
from types import ModuleType
from unittest.mock import MagicMock


def _import_module_bypass_init(module_path: str, module_name: str):
    import importlib.util

    parent_name = "modules.fediway.sources"
    if parent_name not in sys.modules:
        for i, part in enumerate(parent_name.split(".")):
            full_name = ".".join(parent_name.split(".")[: i + 1])
            if full_name not in sys.modules:
                sys.modules[full_name] = ModuleType(full_name)

    base_spec = importlib.util.spec_from_file_location(
        "modules.fediway.sources.base", "modules/fediway/sources/base.py"
    )
    base_module = importlib.util.module_from_spec(base_spec)
    sys.modules["modules.fediway.sources.base"] = base_module
    base_spec.loader.exec_module(base_module)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_smart_follows = _import_module_bypass_init(
    "modules/fediway/sources/statuses/smart_follows.py",
    "modules.fediway.sources.statuses.smart_follows",
)
_follows_engaging = _import_module_bypass_init(
    "modules/fediway/sources/statuses/follows_engaging_now.py",
    "modules.fediway.sources.statuses.follows_engaging_now",
)
_tag_affinity = _import_module_bypass_init(
    "modules/fediway/sources/statuses/tag_affinity.py",
    "modules.fediway.sources.statuses.tag_affinity",
)
_second_degree = _import_module_bypass_init(
    "modules/fediway/sources/statuses/second_degree.py",
    "modules.fediway.sources.statuses.second_degree",
)
_collaborative = _import_module_bypass_init(
    "modules/fediway/sources/statuses/collaborative_filtering.py",
    "modules.fediway.sources.statuses.collaborative_filtering",
)

SmartFollowsSource = _smart_follows.SmartFollowsSource
FollowsEngagingNowSource = _follows_engaging.FollowsEngagingNowSource
TagAffinitySource = _tag_affinity.TagAffinitySource
SecondDegreeSource = _second_degree.SecondDegreeSource
CollaborativeFilteringSource = _collaborative.CollaborativeFilteringSource


def test_sources_have_unique_ids():
    mock_rw = MagicMock()

    smart = SmartFollowsSource(rw=mock_rw, account_id=1)
    follows = FollowsEngagingNowSource(rw=mock_rw, account_id=1)
    tag = TagAffinitySource(rw=mock_rw, account_id=1)
    second = SecondDegreeSource(rw=mock_rw, account_id=1)
    collab = CollaborativeFilteringSource(rw=mock_rw, account_id=1)

    ids = [smart.id, follows.id, tag.id, second.id, collab.id]
    assert len(ids) == len(set(ids)), "Source IDs must be unique"


def test_all_sources_have_tracked_params():
    mock_rw = MagicMock()

    sources = [
        SmartFollowsSource(rw=mock_rw, account_id=1),
        FollowsEngagingNowSource(rw=mock_rw, account_id=1),
        TagAffinitySource(rw=mock_rw, account_id=1),
        SecondDegreeSource(rw=mock_rw, account_id=1),
        CollaborativeFilteringSource(rw=mock_rw, account_id=1),
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
        cfg.smart_follows.weight
        + cfg.follows_engaging_now.weight
        + cfg.tag_affinity.weight
        + cfg.second_degree.weight
        + cfg.collaborative_filtering.weight
        + cfg.trending.weight
    )

    assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"


def test_source_weights_match_plan():
    cfg = SourcesConfig()

    assert cfg.smart_follows.weight == 0.35
    assert cfg.follows_engaging_now.weight == 0.15
    assert cfg.tag_affinity.weight == 0.15
    assert cfg.second_degree.weight == 0.10
    assert cfg.collaborative_filtering.weight == 0.15
    assert cfg.trending.weight == 0.10


def test_all_mvp_sources_enabled_by_default():
    cfg = SourcesConfig()

    assert cfg.smart_follows.enabled
    assert cfg.follows_engaging_now.enabled
    assert cfg.tag_affinity.enabled
    assert cfg.second_degree.enabled
    assert cfg.collaborative_filtering.enabled
    assert cfg.trending.enabled


def test_sources_config_get_enabled_returns_dict():
    cfg = SourcesConfig()
    enabled = cfg.get_enabled_sources()

    assert isinstance(enabled, dict)
    assert "smart_follows" in enabled
    assert "trending" in enabled


def test_sources_config_group_weights():
    cfg = SourcesConfig()
    weights = cfg.get_group_weights()

    # in-network: smart_follows (0.35) + follows_engaging_now (0.15) = 0.5
    assert abs(weights.get("in-network", 0) - 0.5) < 0.01

    # discovery: tag_affinity (0.15) + second_degree (0.1) + cf (0.15) = 0.4
    assert abs(weights.get("discovery", 0) - 0.4) < 0.01

    # trending: 0.1
    assert abs(weights.get("trending", 0) - 0.1) < 0.01


def test_home_sources_includes_fallback_group():
    """Verify get_home_sources includes fallback group for WeightedGroupSampler."""
    with open("apps/api/dependencies/sources/statuses.py") as f:
        content = f.read()
        assert '"_fallback"' in content, "Home sources should include _fallback group"
