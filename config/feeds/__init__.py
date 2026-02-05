"""
Feeds configuration from feeds.toml.

See schema.py for all available settings and defaults.
"""

from .loader import ConfigError, load
from .schema import FeedsTomlConfig

__all__ = [
    "ConfigError",
    "FeedsTomlConfig",
    "load",
]
