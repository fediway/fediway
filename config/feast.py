from feast.feature_store import RepoConfig
from feast.infra.online_stores.redis import RedisOnlineStoreConfig
from feast.repo_config import FeastConfigBaseModel
from pydantic import SecretStr

from .base import BaseConfig
from modules.features.offline_store import RisingwaveOfflineStoreConfig
from modules.features.provider import FediwayProvider


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
            provider="modules.features.provider.FediwayProvider",
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
        from .kafka import KafkaConfig

        db = DBConfig()
        kafka = KafkaConfig()

        return RisingwaveOfflineStoreConfig(
            host=db.rw_host,
            port=db.rw_port,
            database=db.rw_name,
            user=db.rw_user,
            password=db.rw_pass.get_secret_value(),
            kafka_bootstrap_servers=kafka.kafka_bootstrap_servers,
        )
