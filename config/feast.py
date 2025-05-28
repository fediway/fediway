from feast.feature_store import RepoConfig
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres import (
    PostgreSQLOfflineStoreConfig,
)
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from pydantic import SecretStr

from .base import BaseConfig


class FeastConfig(BaseConfig):
    feast_registry: str = "data/features.db"

    feast_online_store_ttl: int = 3600 * 60 * 30

    feast_redis_host: str = "localhost"
    feast_redis_port: int = 6379
    feast_redis_pass: SecretStr = ""

    @property
    def repo_config(self) -> RepoConfig:
        return RepoConfig(
            project="fediway",
            provider="local",
            registry=self.feast_registry,
            online_store=self.online_config,
            offline_store=self.offline_config,
            entity_key_serialization_version=3,
        )

    @property
    def online_config(self):
        connection_string = f"{self.feast_redis_host}:{self.feast_redis_port}"

        if self.feast_redis_pass.get_secret_value() != "":
            connection_string += f",password={self.feast_redis_pass.get_secret_value()}"

        return RedisOnlineStoreConfig(
            connection_string=connection_string,
            key_ttl_seconds=self.feast_online_store_ttl,
        )

    @property
    def offline_config(self):
        from .db import DBConfig

        db = DBConfig()

        return PostgreSQLOfflineStoreConfig(
            host=db.rw_host,
            port=db.rw_port,
            database=db.rw_name,
            user=db.rw_user,
            password=db.rw_pass.get_secret_value(),
        )
