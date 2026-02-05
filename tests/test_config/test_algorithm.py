import tempfile
from pathlib import Path

import pytest

from config.algorithm import (
    ConfigError,
    load_toml_config,
)
from config.algorithm.schema import HomeWeights, SuggestionsWeights


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
        assert config.timelines.home.weights.in_network == 50
        assert config.timelines.home.weights.discovery == 35
        assert config.timelines.home.weights.trending == 15


def test_load_toml_config_minimal():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = 5
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.timelines.home.settings.max_per_author == 5


def test_load_toml_config_custom_weights():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
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
[trends.statuses.settings]
min_engagement = 3
window_hours = 48
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.trends.statuses.settings.min_engagement == 3
        assert config.trends.statuses.settings.window_hours == 48


def test_load_toml_config_suggestions():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[suggestions.settings]
max_results = 50
""")
        f.flush()
        config = load_toml_config(Path(f.name))
        assert config.suggestions.settings.max_results == 50


def test_load_toml_config_complete():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[global]
content_age_hours = 72

[timelines.home.weights]
in_network = 40
discovery = 45
trending = 15

[timelines.home.settings]
max_per_author = 2

[timelines.home.sources.tag_affinity]
boost_tags = ["art", "photography"]

[trends.statuses.settings]
local_only = true

[trends.tags.filters]
blocked_tags = ["politics"]

[suggestions.weights]
social_proof = 50
similar_interests = 30
popular = 20
""")
        f.flush()
        config = load_toml_config(Path(f.name))

        assert config.global_settings.content_age_hours == 72
        assert config.timelines.home.weights.in_network == 40
        assert config.timelines.home.settings.max_per_author == 2
        assert config.trends.statuses.settings.local_only is True
        assert config.trends.tags.filters.blocked_tags == ["politics"]
        assert config.suggestions.weights.social_proof == 50


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
