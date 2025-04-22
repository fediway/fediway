
from feast.feature_store import RepoConfig
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from feast.infra.offline_stores.duckdb import DuckDBOfflineStoreConfig

from enum import Enum

import os
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class OfflineStoreTypes(Enum):
    duckdb: str = "duckdb"
    spark: str  = "spark"

class FeastConfig(BaseConfig):
    feast_registry: str = 'data/features.db'

    feast_offline_store_enabled: bool = False
    feast_offline_store_type: OfflineStoreTypes = OfflineStoreTypes.duckdb
    feast_offline_store_s3_endpoint: str = ''
    

    feast_offline_store_path: str = "data/features"
    feast_spark_s3_endpoint: str = ''
    feast_spark_s3_access_key: SecretStr = ''
    feast_spark_s3_secret_key: SecretStr = ''

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
        if self.feast_offline_store_type == OfflineStoreTypes.duckdb:
            return self.get_duckdb_config()

        if self.feast_offline_store_type == OfflineStoreTypes.spark:
            return self.get_spark_config()

    def get_duckdb_config(self) -> DuckDBOfflineStoreConfig:
        return DuckDBOfflineStoreConfig()

    def get_spark_config(self):
        from feast.infra.offline_stores.contrib.spark_offline_store.spark import SparkOfflineStoreConfig

        spark_conf = {
            "spark.hadoop.fs.s3a.endpoint": self.feast_spark_s3_endpoint,
            "spark.hadoop.fs.s3a.access.key": self.feast_spark_s3_access_key.get_secret_value(),
            "spark.hadoop.fs.s3a.secret.key": self.feast_spark_s3_secret_key.get_secret_value(),
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            # "spark.hadoop.fs.s3a.connection.ssl.enabled": "true",

            # "spark.sql.session.timeZone": "UTC",
            
            # 4) Leave SSL on (or disable if your endpoint is HTTP only)
            # "spark.hadoop.fs.s3a.connection.ssl.enabled": "true",
            # 5) (Optional) Pick your desired file‑size or memory settings…
            
        }


        return SparkOfflineStoreConfig(
            staging_location=self.feast_offline_store_path,
            spark_conf=spark_conf,
        )