from enum import Enum
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

from .base import BaseConfig


class AppEnvTypes(Enum):
    prod: str = "production"
    dev: str = "development"
    test: str = "test"


class AppConfig(BaseConfig):
    debug: bool = False

    app_env: AppEnvTypes = AppEnvTypes.prod
    app_version: str = "v0.0.1"

    app_secret: SecretStr
    app_host: str
    api_url: str

    app_title: str = "Fediway - Algorithmic Feeds for Mastodon ✨"

    data_path: str = "data"
