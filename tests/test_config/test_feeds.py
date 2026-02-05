import tempfile
from pathlib import Path

import pytest

from config.feeds import (
    ConfigError,
    load,
)
from config.feeds.schema import HomeWeights, SuggestionsWeights


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


def test_load_no_file_uses_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load(Path(tmpdir) / "feeds.toml")
        assert config.timelines.home.weights.in_network == 50
        assert config.timelines.home.weights.discovery == 35
        assert config.timelines.home.weights.trending == 15


def test_load_minimal():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = 5
""")
        f.flush()
        config = load(Path(f.name))
        assert config.timelines.home.settings.max_per_author == 5


def test_load_custom_weights():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.weights]
in_network = 70
discovery = 20
trending = 10
""")
        f.flush()
        config = load(Path(f.name))
        assert config.timelines.home.weights.in_network == 70
        assert config.timelines.home.weights.discovery == 20
        assert config.timelines.home.weights.trending == 10


def test_load_invalid_weights_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.weights]
in_network = 60
discovery = 30
trending = 5
""")
        f.flush()
        with pytest.raises(ConfigError) as exc_info:
            load(Path(f.name))
        assert "must sum to 100" in str(exc_info.value)


def test_load_trending():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[trends.statuses.settings]
min_engagement = 3
window_hours = 48
""")
        f.flush()
        config = load(Path(f.name))
        assert config.trends.statuses.settings.min_engagement == 3
        assert config.trends.statuses.settings.window_hours == 48


def test_load_suggestions():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[suggestions.settings]
max_results = 50
""")
        f.flush()
        config = load(Path(f.name))
        assert config.suggestions.settings.max_results == 50


def test_load_complete():
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
        config = load(Path(f.name))

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
    assert "feeds.toml" in formatted
    assert "timelines.home.weights" in formatted
    assert "must sum to 100" in formatted
    assert "Add trending = 10" in formatted


def test_invalid_toml_syntax_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings
max_per_author = 5
""")
        f.flush()
        with pytest.raises(ConfigError) as exc_info:
            load(Path(f.name))
        assert "Invalid TOML syntax" in str(exc_info.value)


def test_out_of_bounds_value_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = 999
""")
        f.flush()
        with pytest.raises(ConfigError):
            load(Path(f.name))


def test_wrong_type_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = "five"
""")
        f.flush()
        with pytest.raises(ConfigError):
            load(Path(f.name))


def test_unknown_source_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.sources.unknown_source]
enabled = true
""")
        f.flush()
        with pytest.raises(ConfigError):
            load(Path(f.name))


def test_default_values_are_sensible():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load(Path(tmpdir) / "feeds.toml")

        # Home timeline defaults
        assert config.timelines.home.settings.batch_size == 20
        assert config.timelines.home.settings.max_per_author == 3
        assert config.timelines.home.settings.diversity_penalty == 0.1

        # Trending defaults
        assert config.trends.statuses.settings.window_hours == 24
        assert config.trends.statuses.settings.max_per_author == 2

        # Suggestions defaults
        assert config.suggestions.settings.max_results == 40

        # Sources enabled by default
        assert config.timelines.home.sources.top_follows.enabled is True
        assert config.timelines.home.sources.engaged_by_friends.enabled is True

        # Similar users disabled by default (experimental)
        assert config.timelines.home.sources.engaged_by_similar_users.enabled is False


def test_partial_weights_rejected():
    """If you override weights, you must provide all three."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.weights]
in_network = 70
""")
        f.flush()
        with pytest.raises(ConfigError) as exc_info:
            load(Path(f.name))
        assert "must sum to 100" in str(exc_info.value)


def test_negative_value_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = -1
""")
        f.flush()
        with pytest.raises(ConfigError):
            load(Path(f.name))


def test_boundary_values_accepted():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.settings]
max_per_author = 1
diversity_penalty = 0.0
batch_size = 100

[timelines.home.weights]
in_network = 100
discovery = 0
trending = 0
""")
        f.flush()
        config = load(Path(f.name))
        assert config.timelines.home.settings.max_per_author == 1
        assert config.timelines.home.settings.diversity_penalty == 0.0
        assert config.timelines.home.settings.batch_size == 100
        assert config.timelines.home.weights.in_network == 100


def test_empty_toml_file_uses_defaults():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("")
        f.flush()
        config = load(Path(f.name))
        assert config.timelines.home.weights.in_network == 50


def test_source_can_be_disabled():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[timelines.home.sources.top_follows]
enabled = false

[timelines.home.sources.tag_affinity]
enabled = false
""")
        f.flush()
        config = load(Path(f.name))
        assert config.timelines.home.sources.top_follows.enabled is False
        assert config.timelines.home.sources.tag_affinity.enabled is False
        # Others remain enabled by default
        assert config.timelines.home.sources.engaged_by_friends.enabled is True


def test_trending_tags_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[trends.tags.settings]
window_hours = 48
min_posts = 5
min_accounts = 3
max_results = 30
local_only = true

[trends.tags.scoring]
weight_posts = 2.0
weight_accounts = 3.0
velocity_boost = false

[trends.tags.filters]
blocked_tags = ["spam", "nsfw"]
""")
        f.flush()
        config = load(Path(f.name))
        assert config.trends.tags.settings.window_hours == 48
        assert config.trends.tags.settings.min_posts == 5
        assert config.trends.tags.settings.local_only is True
        assert config.trends.tags.scoring.weight_posts == 2.0
        assert config.trends.tags.scoring.velocity_boost is False
        assert config.trends.tags.filters.blocked_tags == ["spam", "nsfw"]


def test_config_error_without_path():
    err = ConfigError("Something went wrong")
    formatted = err.format()
    assert "feeds.toml" in formatted
    assert "Something went wrong" in formatted


def test_config_integration_with_main_config():
    """Verify feeds config is accessible via main config object."""
    from config import config

    # Should be able to access feeds config
    assert config.feeds is not None
    assert config.feeds.timelines.home.weights.in_network == 50
    assert config.feeds.trends.statuses.settings.window_hours == 24
    assert config.feeds.suggestions.settings.max_results == 40
