import pytest

from config.sources import SourceConfig, SourcesConfig


def test_source_config_defaults():
    cfg = SourceConfig()

    assert cfg.enabled is True
    assert cfg.weight == 0.1
    assert cfg.limit is None
    assert cfg.params == {}


def test_source_config_custom_values():
    cfg = SourceConfig(
        enabled=False,
        weight=0.5,
        limit=100,
        params={"max_per_author": 3},
    )

    assert cfg.enabled is False
    assert cfg.weight == 0.5
    assert cfg.limit == 100
    assert cfg.params["max_per_author"] == 3


def test_source_config_weight_validation():
    with pytest.raises(ValueError):
        SourceConfig(weight=-0.1)

    with pytest.raises(ValueError):
        SourceConfig(weight=1.5)


def test_sources_config_has_all_mvp_sources():
    cfg = SourcesConfig()

    assert hasattr(cfg, "top_follows")
    assert hasattr(cfg, "engaged_by_friends")
    assert hasattr(cfg, "tag_affinity")
    assert hasattr(cfg, "posted_by_friends_of_friends")
    assert hasattr(cfg, "engaged_by_similar_users")
    assert hasattr(cfg, "trending")


def test_sources_config_default_enabled_state():
    cfg = SourcesConfig()

    assert cfg.top_follows.enabled is True
    assert cfg.engaged_by_friends.enabled is True
    assert cfg.tag_affinity.enabled is True
    assert cfg.posted_by_friends_of_friends.enabled is True
    assert cfg.trending.enabled is True
    assert cfg.engaged_by_similar_users.enabled is True


def test_sources_config_default_weights():
    cfg = SourcesConfig()

    assert cfg.top_follows.weight == 0.35
    assert cfg.engaged_by_friends.weight == 0.15
    assert cfg.tag_affinity.weight == 0.15
    assert cfg.posted_by_friends_of_friends.weight == 0.10
    assert cfg.engaged_by_similar_users.weight == 0.15
    assert cfg.trending.weight == 0.10


def test_sources_config_has_default_params():
    cfg = SourcesConfig()

    assert cfg.top_follows.params["max_per_author"] == 3
    assert cfg.top_follows.params["recency_half_life_hours"] == 12
    assert cfg.trending.params["min_engagers"] == 3
    assert cfg.trending.params["gravity"] == 1.5


def test_sources_config_get_enabled_sources():
    cfg = SourcesConfig()

    enabled = cfg.get_enabled_sources()

    assert "engaged_by_similar_users" in enabled
    assert "top_follows" in enabled
    assert "trending" in enabled


def test_sources_config_get_group_weights():
    cfg = SourcesConfig()

    weights = cfg.get_group_weights()

    # in-network: top_follows (0.35) + engaged_by_friends (0.15) = 0.5
    assert weights["in-network"] == pytest.approx(0.5, rel=0.01)
    # discovery: tag_affinity (0.15) + posted_by_friends_of_friends (0.10) + engaged_by_similar_users (0.15) = 0.4
    assert weights["discovery"] == pytest.approx(0.40, rel=0.01)
    assert weights["trending"] == pytest.approx(0.10, rel=0.01)


def test_sources_config_get_source_config():
    cfg = SourcesConfig()

    top_follows = cfg.get_source_config("top_follows")
    assert top_follows is not None
    assert top_follows.weight == 0.35

    unknown = cfg.get_source_config("unknown_source")
    assert unknown is None


def test_sources_config_from_dict():
    data = {
        "top_follows": {
            "enabled": True,
            "weight": 0.4,
            "params": {"max_per_author": 5},
        },
        "trending": {
            "enabled": False,
        },
    }

    cfg = SourcesConfig(**data)

    assert cfg.top_follows.weight == 0.4
    assert cfg.top_follows.params["max_per_author"] == 5
    assert cfg.trending.enabled is False


def test_sources_config_partial_override():
    data = {
        "top_follows": {
            "weight": 0.5,
        },
    }

    cfg = SourcesConfig(**data)

    assert cfg.top_follows.weight == 0.5
    assert cfg.top_follows.enabled is True


def test_sources_config_custom_source():
    data = {
        "custom_source": {
            "enabled": True,
            "weight": 0.05,
            "params": {"custom_param": "value"},
        },
    }

    cfg = SourcesConfig(**data)

    assert hasattr(cfg, "custom_source") or "custom_source" in cfg.model_extra


def test_fediway_config_has_sources():
    from config.fediway import FediwayConfig

    cfg = FediwayConfig()

    assert hasattr(cfg, "sources")
    assert isinstance(cfg.sources, SourcesConfig)


def test_fediway_config_is_source_enabled():
    from config.fediway import FediwayConfig

    cfg = FediwayConfig()

    assert cfg.is_source_enabled("top_follows") is True
    assert cfg.is_source_enabled("engaged_by_similar_users") is True
    assert cfg.is_source_enabled("unknown") is False


def test_fediway_config_get_source_param():
    from config.fediway import FediwayConfig

    cfg = FediwayConfig()

    assert cfg.get_source_param("top_follows", "max_per_author") == 3
    assert cfg.get_source_param("top_follows", "unknown_param", "default") == "default"
    assert cfg.get_source_param("unknown_source", "param", "default") == "default"
