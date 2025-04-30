
from feast.feature_store import RepoConfig
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres import PostgreSQLOfflineStoreConfig

from enum import Enum

import os
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class FeastConfig(BaseConfig):
    feast_registry: str = 'data/features.db'

    feast_offline_store_enabled: bool = False
    feast_offline_store_s3_endpoint: str = ''
    feast_offline_store_path: str = 'data/features'
    feast_spark_checkpoint_location: str = 'data/features-staging'
    feast_spark_staging_location: str = 'data/features-checkpoint'

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
        from .db import DBConfig
        db = DBConfig()

        return PostgreSQLOfflineStoreConfig(
            host=db.rw_host,
            port=db.rw_port,
            database=db.rw_name,
            user=db.rw_user,
            password=db.rw_pass.get_secret_value(),
        )

        # spark_conf = {
        #     'spark.master': 'local[*]',
        #     'spark.sql.session.timeZone': 'UTC'
        # }

        # if self.feast_offline_store_path.startswith("s3a://"):
        #     spark_conf["spark.hadoop.fs.s3a.access.key"] = os.environ['AWS_ACCESS_KEY_ID']
        #     spark_conf["spark.hadoop.fs.s3a.secret.key"] = os.environ['AWS_SECRET_ACCESS_KEY']
        #     spark_conf["spark.hadoop.fs.s3a.impl"] = "org.apache.hadoop.fs.s3a.S3AFileSystem"
        #     spark_conf["spark.hadoop.fs.s3a.path.style.access"] = "true"
        #     spark_conf["spark.jars.packages"] = "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026"

        # return SparkOfflineStoreConfig(
        #     spark_conf=spark_conf,
        #     staging_location=self.feast_spark_staging_location
        # )