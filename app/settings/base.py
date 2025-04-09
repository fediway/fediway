
import sys
from enum import Enum
from loguru import logger
from sqlalchemy import URL
import logging

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

class AppEnvTypes(Enum):
    prod: str = "production"
    dev: str = "development"
    test: str = "test"

class BaseAppSettings(BaseSettings):
    app_env: AppEnvTypes = AppEnvTypes.prod

    class Config:
        env_file = ".env"
        extra = "ignore"

class AppSettings(BaseAppSettings):
    debug: bool = False
    docs_url: str = "/docs"
    openapi_prefix: str = ""
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"
    title: str = "Algorithmic Feeds for the Fediverse"
    version: str = "0.0.0"

    session_max_size: int = 10_000
    session_max_age_in_seconds: int = 6_000
    session_cookie_name: str = 'session_id'

    feed_max_age_in_days: int = 7
    feed_max_light_candidates: int = 1000
    feed_max_heavy_candidates: int = 100
    feed_samples_page_size: int = 10

    broker_url: RedisDsn
    
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "mastodon"
    db_pass: str = ""
    db_name: str = "mastodon_development"

    app_secret: SecretStr
    app_host: str

    api_prefix: str = "/api"

    jwt_token_prefix: str = "Token"

    allowed_hosts: list[str] = ["*", "http://localhost:3000"]

    ipv4_location_file: str | None = None
    ipv6_location_file: str | None = None

    logging_level: int = logging.INFO
    loggers: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    class Config:
        validate_assignment = True

    def get_database_url(self):
        return URL.create(
            "postgresql",
            username=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            database=self.db_name,
        )

    @property
    def fastapi_kwargs(self) -> dict[str, any]:
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            # "openapi_prefix": self.openapi_prefix,
            # "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }

    def configure_logging(self) -> None:
        from app.core.logging import InterceptHandler

        logging.getLogger().handlers = [InterceptHandler()]
        
        for logger_name in self.loggers:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler(level=self.logging_level)]

        logger.configure(handlers=[{"sink": sys.stderr, "level": self.logging_level}])