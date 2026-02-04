import tempfile
from pathlib import Path

import pytest

from config.algorithm import (
    ConfigError,
    load_toml_config,
)
from config.algorithm.loader import deep_merge, load_preset
from config.algorithm.schema import HomeWeights, SuggestionsWeights


def test_deep_merge_simple():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested():
    base = {"a": {"x": 1, "y": 2}}
    override = {"a": {"y": 3}}
    result = deep_merge(base, override)
    assert result == {"a": {"x": 1, "y": 3}}


def test_deep_merge_override_replaces_non_dict():
    base = {"a": {"x": 1}}
    override = {"a": 5}
    result = deep_merge(base, override)
    assert result == {"a": 5}


def test_load_preset_home_balanced():
    preset = load_preset("home", "balanced")
    assert preset["weights"]["in_network"] == 50
    assert preset["weights"]["discovery"] == 35
    assert preset["weights"]["trending"] == 15


def test_load_preset_home_discovery():
    preset = load_preset("home", "discovery")
    assert preset["weights"]["discovery"] == 50


def test_load_preset_trending_viral():
    preset = load_preset("trending", "viral")
    assert preset["settings"]["window_hours"] == 24


def test_load_preset_suggestions_balanced():
    preset = load_preset("suggestions", "balanced")
    assert preset["weights"]["social_proof"] == 40


def test_load_preset_invalid_raises_error():
    with pytest.raises(ConfigError) as exc_info:
        load_preset("home", "nonexistent")
    assert "Unknown preset" in str(exc_info.value)
    assert "Valid presets" in str(exc_info.value)


def test_home_weights_valid():
    weights = HomeWeights(in_network=50, discovery=30, trending=20)
    assert weights.in_network == 50


def test_home_weights_must_sum_to_100():
    with pytest.raises(ValueError) as exc_info:
        HomeWeights(in_network=50, discovery=30, trending=10)
    assert "must sum to 100" in str(exc_info.value)


def test_suggestions_weights_valid():
    weights = SuggestionsWeights(social_proof=40, similar_interests=35, popular=25)
    assert weights.social_proof == 40


def test_suggestions_weights_must_sum_to_100():
    with pytest.raises(ValueError) as exc_info:
        SuggestionsWeights(social_proof=50, similar_interests=30, popular=10)
    assert "must sum to 100" in str(exc_info.value)


def test_load_toml_config_no_file_uses_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_toml_config(Path(tmpdir) / "fediway.toml")
        assert config.timelines.home.preset == "balanced"
        assert config.trends.statuses.preset == "viral"
        assert config.suggestions.preset == "balanced"


def test_load_toml_config_minimal():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home]
preset = "discovery"
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.timelines.home.preset == "discovery"


def test_load_toml_config_preset_with_overrides():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home]
preset = "balanced"

[timelines.home.settings]
max_per_author = 5
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.timelines.home.settings.max_per_author == 5
        assert config.timelines.home.settings.batch_size == 20


def test_load_toml_config_custom_weights():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home]
preset = "balanced"

[timelines.home.weights]
in_network = 70
discovery = 20
trending = 10
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.timelines.home.weights.in_network == 70
        assert config.timelines.home.weights.discovery == 20
        assert config.timelines.home.weights.trending == 10


def test_load_toml_config_invalid_weights_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home]
preset = "balanced"

[timelines.home.weights]
in_network = 60
discovery = 30
trending = 5
""")
        f.flush()
        with pytest.raises(ConfigError) as exc_info:
            load_toml_config(Path(f.name))
        assert "must sum to 100" in str(exc_info.value)


def test_load_toml_config_trending():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[trends.statuses]
preset = "local"

[trends.statuses.settings]
min_engagement = 3
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.trends.statuses.preset == "local"
        assert config.trends.statuses.settings.min_engagement == 3


def test_load_toml_config_suggestions():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[suggestions]
preset = "similar"

[suggestions.settings]
max_results = 50
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.suggestions.preset == "similar"
        assert config.suggestions.settings.max_results == 50


def test_load_toml_config_complete():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[global]
content_age_hours = 72

[timelines.home]
preset = "discovery"

[timelines.home.weights]
in_network = 40
discovery = 45
trending = 15

[timelines.home.settings]
max_per_author = 2

[timelines.home.sources.tag_affinity]
boost_tags = ["art", "photography"]

[trends.statuses]
preset = "local"

[trends.tags]
preset = "default"

[trends.tags.filters]
blocked_tags = ["politics"]

[suggestions]
preset = "similar"
""")
        f.flush()
        config = load_toml_config(Path(f.name))

        assert config.global_settings.content_age_hours == 72
        assert config.timelines.home.preset == "discovery"
        assert config.timelines.home.weights.in_network == 40
        assert config.timelines.home.settings.max_per_author == 2
        assert config.trends.statuses.preset == "local"
        assert config.trends.tags.filters.blocked_tags == ["politics"]
        assert config.suggestions.preset == "similar"


def test_config_error_formatting():
    err = ConfigError(
        "Weights must sum to 100",
        path="timelines.home.weights",
        hint="Add trending = 10",
    )
    formatted = err.format()
    assert "fediway.toml" in formatted
    assert "timelines.home.weights" in formatted
    assert "must sum to 100" in formatted
    assert "Add trending = 10" in formatted
