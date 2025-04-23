
from feast.feature_store import RepoConfig
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from feast.infra.offline_stores.duckdb import DuckDBOfflineStoreConfig

from enum import Enum

import os
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class OfflineStoreType(Enum):
    duckdb: str = "duckdb"
    spark: str = "spark"

class FeastConfig(BaseConfig):
    feast_registry: str = 'data/features.db'

    feast_offline_store_enabled: bool = False
    feast_offline_store_type: OfflineStoreType = OfflineStoreType.duckdb
    feast_offline_store_s3_endpoint: str = ''

    feast_offline_store_path: str = "data/features"

    feast_spark_checkpoint_location: str = ''

    feast_redis_host: str       = 'localhost'
    feast_redis_port: int       = 6379
    feast_redis_pass: SecretStr = ""

    @property
    def repo_config(self) -> RepoConfig:
        return RepoConfig(
            project='fediway',
            provider='local',
            registry=self.feast_registry,
            online_store=self.online_config,
            offline_store=self.offline_config,
            entity_key_serialization_version=3,
        )

    @property
    def online_config(self):
        connection_string = f"{self.feast_redis_host}:{self.feast_redis_port}"

        if self.feast_redis_pass.get_secret_value() != '':
            connection_string += f",password={self.feast_redis_pass.get_secret_value()}"

        return RedisOnlineStoreConfig(
            connection_string=connection_string
        )

    @property
    def offline_config(self):
        if self.feast_offline_store_type == OfflineStoreType.duckdb:
            return self.get_duckdb_config()

        raise NotImplementedError

    def get_duckdb_config(self) -> DuckDBOfflineStoreConfig:
        return DuckDBOfflineStoreConfig()