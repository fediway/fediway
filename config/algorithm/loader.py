"""
TOML configuration loader for fediway algorithms.

Handles loading fediway.toml, merging with presets, and validation.
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

PRESETS_DIR = Path(__file__).parent / "presets"

HOME_PRESETS = ["balanced", "discovery", "local", "chronological"]
TRENDING_STATUSES_PRESETS = ["viral", "local", "curated"]
TRENDING_TAGS_PRESETS = ["default", "local"]
SUGGESTIONS_PRESETS = ["balanced", "similar", "popular"]


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


def load_preset(preset_type: str, preset_name: str) -> dict[str, Any]:
    """Load a preset TOML file."""
    preset_file = PRESETS_DIR / f"{preset_type}_{preset_name}.toml"

    if not preset_file.exists():
        valid = _get_valid_presets(preset_type)
        raise ConfigError(
            f"Unknown preset '{preset_name}'",
            path="*.preset",
            hint=f"Valid presets: {', '.join(valid)}",
        )

    with open(preset_file, "rb") as f:
        return tomllib.load(f)


def _get_valid_presets(preset_type: str) -> list[str]:
    """Get valid preset names for a type."""
    if preset_type == "home":
        return HOME_PRESETS
    elif preset_type == "trending":
        return TRENDING_STATUSES_PRESETS
    elif preset_type == "tags":
        return TRENDING_TAGS_PRESETS
    elif preset_type == "suggestions":
        return SUGGESTIONS_PRESETS
    return []


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts, with override taking precedence."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _apply_home_preset(config: dict) -> dict:
    """Apply preset to home timeline config."""
    preset_name = config.get("preset", "balanced")
    if preset_name == "none":
        return config

    preset = load_preset("home", preset_name)
    return deep_merge(preset, config)


def _apply_trending_statuses_preset(config: dict) -> dict:
    """Apply preset to trending statuses config."""
    preset_name = config.get("preset", "viral")
    if preset_name == "none":
        return config

    preset = load_preset("trending", preset_name)
    return deep_merge(preset, config)


def _apply_suggestions_preset(config: dict) -> dict:
    """Apply preset to suggestions config."""
    preset_name = config.get("preset", "balanced")
    if preset_name == "none":
        return config

    preset = load_preset("suggestions", preset_name)
    return deep_merge(preset, config)


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

    # Start with empty config (will use defaults)
    raw_config: dict[str, Any] = {}

    # Load TOML if exists
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                raw_config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Invalid TOML syntax: {e}")

    # Apply presets to each section
    if "timelines" in raw_config and "home" in raw_config["timelines"]:
        raw_config["timelines"]["home"] = _apply_home_preset(raw_config["timelines"]["home"])

    if "trends" in raw_config and "statuses" in raw_config["trends"]:
        raw_config["trends"]["statuses"] = _apply_trending_statuses_preset(
            raw_config["trends"]["statuses"]
        )

    if "suggestions" in raw_config:
        raw_config["suggestions"] = _apply_suggestions_preset(raw_config["suggestions"])

    # Validate with Pydantic
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
