"""
TOML configuration loader for fediway algorithms.

Handles loading fediway.toml and validation.
"""

from pathlib import Path
from typing import Any

import tomllib
from pydantic import ValidationError

from .schema import (
    FediwayTomlConfig,
    HomeTimelineConfig,
    SuggestionsConfig,
    TrendingStatusesConfig,
    TrendingTagsConfig,
)


class ConfigError(Exception):
    """Configuration error with user-friendly message."""

    def __init__(self, message: str, path: str | None = None, hint: str | None = None):
        self.message = message
        self.path = path
        self.hint = hint
        super().__init__(self.format())

    def format(self) -> str:
        lines = ["Error in fediway.toml:"]
        if self.path:
            lines.append(f"  at [{self.path}]")
        lines.append(f"  {self.message}")
        if self.hint:
            lines.append(f"  Hint: {self.hint}")
        return "\n".join(lines)


def load_toml_config(config_path: Path | None = None) -> FediwayTomlConfig:
    """
    Load and validate fediway.toml configuration.

    Args:
        config_path: Path to fediway.toml. If None, looks in current directory.

    Returns:
        Validated FediwayTomlConfig instance.

    Raises:
        ConfigError: If configuration is invalid.
    """
    if config_path is None:
        config_path = Path("fediway.toml")

    raw_config: dict[str, Any] = {}

    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                raw_config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Invalid TOML syntax: {e}")

    try:
        return FediwayTomlConfig(**raw_config)
    except ValidationError as e:
        errors = e.errors()
        if errors:
            err = errors[0]
            path = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            raise ConfigError(msg, path=path)
        raise ConfigError(str(e))


def get_home_config(toml_config: FediwayTomlConfig | None = None) -> HomeTimelineConfig:
    """Get home timeline configuration."""
    if toml_config is None:
        toml_config = load_toml_config()
    return toml_config.timelines.home


def get_trending_statuses_config(
    toml_config: FediwayTomlConfig | None = None,
) -> TrendingStatusesConfig:
    """Get trending statuses configuration."""
    if toml_config is None:
        toml_config = load_toml_config()
    return toml_config.trends.statuses


def get_trending_tags_config(
    toml_config: FediwayTomlConfig | None = None,
) -> TrendingTagsConfig:
    """Get trending tags configuration."""
    if toml_config is None:
        toml_config = load_toml_config()
    return toml_config.trends.tags


def get_suggestions_config(
    toml_config: FediwayTomlConfig | None = None,
) -> SuggestionsConfig:
    """Get suggestions configuration."""
    if toml_config is None:
        toml_config = load_toml_config()
    return toml_config.suggestions


class AlgorithmConfig:
    """
    Singleton access to algorithm configuration.

    Usage:
        from config.algorithm import algorithm_config

        home = algorithm_config.home
        trending = algorithm_config.trends.statuses
    """

    _instance: "AlgorithmConfig | None" = None
    _config: FediwayTomlConfig | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_loaded(self):
        if self._config is None:
            self._config = load_toml_config()

    def reload(self, config_path: Path | None = None):
        """Reload configuration from disk."""
        self._config = load_toml_config(config_path)

    @property
    def home(self) -> HomeTimelineConfig:
        self._ensure_loaded()
        return self._config.timelines.home

    @property
    def trends(self) -> "TrendsConfigAccess":
        self._ensure_loaded()
        return TrendsConfigAccess(self._config.trends)

    @property
    def suggestions(self) -> SuggestionsConfig:
        self._ensure_loaded()
        return self._config.suggestions

    @property
    def raw(self) -> FediwayTomlConfig:
        """Access raw config for advanced use."""
        self._ensure_loaded()
        return self._config


class TrendsConfigAccess:
    """Helper for accessing trends sub-configs."""

    def __init__(self, trends_config):
        self._trends = trends_config

    @property
    def statuses(self) -> TrendingStatusesConfig:
        return self._trends.statuses

    @property
    def tags(self) -> TrendingTagsConfig:
        return self._trends.tags


# Singleton instance
algorithm_config = AlgorithmConfig()
