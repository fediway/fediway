from unittest.mock import MagicMock, patch

from config import config
from config.feeds.schema import (
    FeedsTomlConfig,
    HomeSources,
    SourceConfig,
    SuggestionsPopularConfig,
    SuggestionsSimilarInterestsConfig,
    SuggestionsSocialProofConfig,
    SuggestionsSourcesConfig,
    TrendingTagsConfig,
)
from config.risingwave import RisingWaveConfig


def _mock_fediway_config(**flags):
    mock = MagicMock()
    mock.kafka_enabled = flags.get("kafka_enabled", False)
    mock.collaborative_filtering_enabled = flags.get("collaborative_filtering_enabled", False)
    mock.orbit_enabled = flags.get("orbit_enabled", False)
    mock.features_online_enabled = flags.get("features_online_enabled", False)
    mock.features_offline_enabled = flags.get("features_offline_enabled", False)
    return mock


def _mock_feeds_config(source_flags=None, suggestion_flags=None, trends_flags=None):
    """Create feeds config with all sources disabled by default."""
    source_flags = source_flags or {}
    suggestion_flags = suggestion_flags or {}
    trends_flags = trends_flags or {}

    disabled = SourceConfig(enabled=False)
    sources = HomeSources(
        top_follows=source_flags.get("top_follows", disabled),
        engaged_by_friends=source_flags.get("engaged_by_friends", disabled),
        tag_affinity=source_flags.get("tag_affinity", disabled),
        posted_by_friends_of_friends=source_flags.get("posted_by_friends_of_friends", disabled),
        trending=source_flags.get("trending", disabled),
        engaged_by_similar_users=source_flags.get("engaged_by_similar_users", disabled),
        popular_posts=source_flags.get("popular_posts", disabled),
    )

    suggestion_sources = SuggestionsSourcesConfig(
        social_proof=suggestion_flags.get(
            "social_proof", SuggestionsSocialProofConfig(enabled=False)
        ),
        similar_interests=suggestion_flags.get(
            "similar_interests", SuggestionsSimilarInterestsConfig(enabled=False)
        ),
        popular=suggestion_flags.get("popular", SuggestionsPopularConfig(enabled=False)),
    )

    feeds = FeedsTomlConfig()
    feeds.timelines.home.sources = sources
    feeds.suggestions.sources = suggestion_sources
    if "tags" in trends_flags:
        feeds.trends.tags = trends_flags["tags"]
    return feeds


def _patch_configs(fediway_flags=None, source_flags=None, suggestion_flags=None, trends_flags=None):
    """Context manager helper to patch both fediway and feeds config."""
    fediway_flags = fediway_flags or {}
    source_flags = source_flags or {}
    suggestion_flags = suggestion_flags or {}
    trends_flags = trends_flags or {}

    class _Ctx:
        def __enter__(self):
            self._p1 = patch.object(config, "fediway", _mock_fediway_config(**fediway_flags))
            self._p2 = patch.object(
                config,
                "feeds",
                _mock_feeds_config(
                    source_flags=source_flags,
                    suggestion_flags=suggestion_flags,
                    trends_flags=trends_flags,
                ),
            )
            self._p1.__enter__()
            self._p2.__enter__()
            return self

        def __exit__(self, *args):
            self._p2.__exit__(*args)
            self._p1.__exit__(*args)

    return _Ctx()


# rw_migrations_paths computed property tests


def test_migrations_paths_base_always_present():
    with _patch_configs():
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/00_base" in paths
    assert "migrations/risingwave/02_engagement" in paths


def test_migrations_paths_kafka_enabled():
    with _patch_configs(fediway_flags={"kafka_enabled": True}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/01_feed" in paths
    assert "migrations/risingwave/07_sinks" in paths


def test_migrations_paths_kafka_disabled():
    with _patch_configs(fediway_flags={"kafka_enabled": False}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/01_feed" not in paths
    assert "migrations/risingwave/07_sinks" not in paths


def test_migrations_paths_collaborative_filtering_enabled():
    with _patch_configs(fediway_flags={"collaborative_filtering_enabled": True}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_collaborative_filtering" in paths


def test_migrations_paths_collaborative_filtering_disabled():
    with _patch_configs(fediway_flags={"collaborative_filtering_enabled": False}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_collaborative_filtering" not in paths


def test_migrations_paths_orbit_enabled():
    with _patch_configs(fediway_flags={"orbit_enabled": True}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/06_orbit" in paths


def test_migrations_paths_orbit_disabled():
    with _patch_configs(fediway_flags={"orbit_enabled": False}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/06_orbit" not in paths


def test_migrations_paths_features_online_enabled():
    with _patch_configs(fediway_flags={"features_online_enabled": True}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/04_features_online" in paths


def test_migrations_paths_features_offline_enabled():
    with _patch_configs(fediway_flags={"features_offline_enabled": True}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/05_features_offline" in paths


def test_migrations_paths_trending_source_enabled():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"trending": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_trending" in paths


def test_migrations_paths_trending_source_disabled():
    with _patch_configs():
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_trending" not in paths


def test_migrations_paths_top_follows_enables_affinity():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"top_follows": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/08_affinity" in paths


def test_migrations_paths_engaged_by_friends_enables_affinity_and_social_proof():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"engaged_by_friends": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/08_affinity" in paths
    assert "migrations/risingwave/10_social_proof" in paths


def test_migrations_paths_tag_affinity_enables_affinity_and_discovery():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"tag_affinity": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/08_affinity" in paths
    assert "migrations/risingwave/09_discovery" in paths


def test_migrations_paths_engaged_by_similar_users_enables_affinity():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"engaged_by_similar_users": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/08_affinity" in paths


def test_migrations_paths_popular_posts_enables_affinity():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(source_flags={"popular_posts": enabled}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/08_affinity" in paths


def test_migrations_paths_trending_tags_enables_trending():
    with _patch_configs(trends_flags={"tags": TrendingTagsConfig(enabled=True)}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_trending" in paths


def test_migrations_paths_trending_tags_disabled():
    with _patch_configs(trends_flags={"tags": TrendingTagsConfig(enabled=False)}):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_trending" not in paths


def test_migrations_paths_similar_interests_enables_discovery():
    with _patch_configs(
        suggestion_flags={"similar_interests": SuggestionsSimilarInterestsConfig(enabled=True)},
    ):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/09_discovery" in paths


def test_migrations_paths_popular_accounts_enables_discovery():
    with _patch_configs(
        suggestion_flags={"popular": SuggestionsPopularConfig(enabled=True)},
    ):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/09_discovery" in paths


def test_migrations_paths_multiple_flags():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(
        fediway_flags={
            "kafka_enabled": True,
            "collaborative_filtering_enabled": True,
            "orbit_enabled": True,
            "features_online_enabled": True,
            "features_offline_enabled": True,
        },
        source_flags={
            "trending": enabled,
            "top_follows": enabled,
            "engaged_by_friends": enabled,
            "tag_affinity": enabled,
        },
    ):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/01_feed" in paths
    assert "migrations/risingwave/02_engagement" in paths
    assert "migrations/risingwave/03_collaborative_filtering" in paths
    assert "migrations/risingwave/03_trending" in paths
    assert "migrations/risingwave/04_features_online" in paths
    assert "migrations/risingwave/05_features_offline" in paths
    assert "migrations/risingwave/06_orbit" in paths
    assert "migrations/risingwave/07_sinks" in paths
    assert "migrations/risingwave/08_affinity" in paths
    assert "migrations/risingwave/09_discovery" in paths
    assert "migrations/risingwave/10_social_proof" in paths


def test_migrations_paths_order_preserved():
    enabled = SourceConfig(enabled=True)
    with _patch_configs(
        fediway_flags={
            "kafka_enabled": True,
            "collaborative_filtering_enabled": True,
            "orbit_enabled": True,
            "features_online_enabled": True,
            "features_offline_enabled": True,
        },
        source_flags={
            "trending": enabled,
            "top_follows": enabled,
            "engaged_by_friends": enabled,
            "tag_affinity": enabled,
        },
    ):
        paths = RisingWaveConfig().rw_migrations_paths

    folder_numbers = [int(p.split("/")[-1].split("_")[0]) for p in paths]
    assert folder_numbers == sorted(folder_numbers)


def test_migrations_paths_all_disabled_returns_base_only():
    with _patch_configs():
        paths = RisingWaveConfig().rw_migrations_paths

    assert len(paths) == 2
    assert paths == [
        "migrations/risingwave/00_base",
        "migrations/risingwave/02_engagement",
    ]
