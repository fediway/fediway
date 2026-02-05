"""
Loads and validates feeds.toml configuration.
"""

from pathlib import Path
from typing import Any

import tomllib
from pydantic import ValidationError

from .schema import FeedsTomlConfig


class ConfigError(Exception):
    """Configuration error with user-friendly message."""

    def __init__(self, message: str, path: str | None = None, hint: str | None = None):
        self.message = message
        self.path = path
        self.hint = hint
        super().__init__(self.format())

    def format(self) -> str:
        lines = ["Error in feeds.toml:"]
        if self.path:
            lines.append(f"  at [{self.path}]")
        lines.append(f"  {self.message}")
        if self.hint:
            lines.append(f"  Hint: {self.hint}")
        return "\n".join(lines)


def load(path: Path | None = None) -> FeedsTomlConfig:
    """
    Load and validate feeds.toml.

    Returns defaults if file doesn't exist.
    """
    if path is None:
        path = Path("feeds.toml")

    raw: dict[str, Any] = {}

    if path.exists():
        try:
            with open(path, "rb") as f:
                raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Invalid TOML syntax: {e}")

    try:
        return FeedsTomlConfig(**raw)
    except ValidationError as e:
        err = e.errors()[0]
        raise ConfigError(err["msg"], path=".".join(str(p) for p in err["loc"]))
