"""
Algorithm configuration module.

Provides TOML-based configuration for fediway recommendation algorithms.

Usage:
    from config.algorithm import algorithm_config

    # Access home timeline config
    home = algorithm_config.home
    print(home.preset)  # "balanced"
    print(home.settings.max_per_author)  # 3

    # Access trending config
    trending = algorithm_config.trends.statuses
    print(trending.settings.window_hours)  # 24

    # Access suggestions config
    suggestions = algorithm_config.suggestions
    print(suggestions.weights.social_proof)  # 40
"""

from .loader import (
    AlgorithmConfig,
    ConfigError,
    algorithm_config,
    get_home_config,
    get_suggestions_config,
    get_trending_statuses_config,
    get_trending_tags_config,
    load_toml_config,
)
from .schema import (
    FediwayTomlConfig,
    HomeTimelineConfig,
    SuggestionsConfig,
    TrendingStatusesConfig,
    TrendingTagsConfig,
)

__all__ = [
    "algorithm_config",
    "AlgorithmConfig",
    "ConfigError",
    "load_toml_config",
    "get_home_config",
    "get_trending_statuses_config",
    "get_trending_tags_config",
    "get_suggestions_config",
    "FediwayTomlConfig",
    "HomeTimelineConfig",
    "TrendingStatusesConfig",
    "TrendingTagsConfig",
    "SuggestionsConfig",
]
