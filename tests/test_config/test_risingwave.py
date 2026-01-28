from unittest.mock import patch, MagicMock

import pytest

from config import config
from config.risingwave import RisingWaveConfig


def _mock_fediway_config(**flags):
    mock = MagicMock()
    mock.collaborative_filtering_enabled = flags.get("collaborative_filtering_enabled", False)
    mock.orbit_enabled = flags.get("orbit_enabled", False)
    mock.features_online_enabled = flags.get("features_online_enabled", False)
    mock.features_offline_enabled = flags.get("features_offline_enabled", False)
    return mock


# rw_migrations_paths computed property tests (12.5)

def test_migrations_paths_base_always_present():
    with patch.object(config, "fediway", _mock_fediway_config()):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/00_base" in paths
    assert "migrations/risingwave/01_feed" in paths
    assert "migrations/risingwave/02_engagement" in paths


def test_migrations_paths_collaborative_filtering_enabled():
    with patch.object(config, "fediway", _mock_fediway_config(collaborative_filtering_enabled=True)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_collaborative_filtering" in paths


def test_migrations_paths_collaborative_filtering_disabled():
    with patch.object(config, "fediway", _mock_fediway_config(collaborative_filtering_enabled=False)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_collaborative_filtering" not in paths


def test_migrations_paths_orbit_enabled():
    with patch.object(config, "fediway", _mock_fediway_config(orbit_enabled=True)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/06_orbit" in paths


def test_migrations_paths_orbit_disabled():
    with patch.object(config, "fediway", _mock_fediway_config(orbit_enabled=False)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/06_orbit" not in paths


def test_migrations_paths_features_online_enabled():
    with patch.object(config, "fediway", _mock_fediway_config(features_online_enabled=True)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/04_features_online" in paths


def test_migrations_paths_features_offline_enabled():
    with patch.object(config, "fediway", _mock_fediway_config(features_offline_enabled=True)):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/05_features_offline" in paths


def test_migrations_paths_multiple_flags():
    with patch.object(config, "fediway", _mock_fediway_config(
        collaborative_filtering_enabled=True,
        orbit_enabled=True,
        features_online_enabled=True,
        features_offline_enabled=True,
    )):
        paths = RisingWaveConfig().rw_migrations_paths

    assert "migrations/risingwave/03_collaborative_filtering" in paths
    assert "migrations/risingwave/04_features_online" in paths
    assert "migrations/risingwave/05_features_offline" in paths
    assert "migrations/risingwave/06_orbit" in paths


def test_migrations_paths_order_preserved():
    with patch.object(config, "fediway", _mock_fediway_config(
        collaborative_filtering_enabled=True,
        orbit_enabled=True,
        features_online_enabled=True,
        features_offline_enabled=True,
    )):
        paths = RisingWaveConfig().rw_migrations_paths

    folder_numbers = [int(p.split("/")[-1].split("_")[0]) for p in paths]
    assert folder_numbers == sorted(folder_numbers)


def test_migrations_paths_all_disabled_returns_base_only():
    with patch.object(config, "fediway", _mock_fediway_config()):
        paths = RisingWaveConfig().rw_migrations_paths

    assert len(paths) == 3
    assert paths == [
        "migrations/risingwave/00_base",
        "migrations/risingwave/01_feed",
        "migrations/risingwave/02_engagement",
    ]
