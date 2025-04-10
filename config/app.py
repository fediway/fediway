
from enum import Enum
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

from .base import BaseConfig

class AppEnvTypes(Enum):
    prod: str = "production"
    dev: str = "development"
    test: str = "test"

class AppConfig(BaseConfig):
    app_env: AppEnvTypes = AppEnvTypes.prod
    app_secret: SecretStr
    app_host: str