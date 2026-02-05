from pydantic import SecretStr

from .base import BaseConfig

try:
    from feast.feature_store import RepoConfig
    from feast.infra.online_stores.redis import RedisOnlineStoreConfig

    FEAST_AVAILABLE = True
except ImportError:
    FEAST_AVAILABLE = False
    RepoConfig = None
    RedisOnlineStoreConfig = None


class FeastConfig(BaseConfig):
    feast_registry: str = "data/features.db"

    offline_store_enabled: bool = True
    feast_online_store_ttl: int = 3600 * 60 * 30

    feast_redis_host: str = "localhost"
    feast_redis_port: int = 6379
    feast_redis_pass: SecretStr = ""

    @staticmethod
    def is_available() -> bool:
        """Check if feast is installed."""
        return FEAST_AVAILABLE

    @property
    def repo_config(self):
        if not FEAST_AVAILABLE:
            raise ImportError("Feast is not installed. Install with: uv sync --extra features")

        from feast.feature_store import RepoConfig

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
        if not FEAST_AVAILABLE:
            raise ImportError("Feast is not installed. Install with: uv sync --extra features")

        from feast.infra.online_stores.redis import RedisOnlineStoreConfig

        connection_string = f"{self.feast_redis_host}:{self.feast_redis_port}"

        if self.feast_redis_pass.get_secret_value() != "":
            connection_string += f",password={self.feast_redis_pass.get_secret_value()}"

        return RedisOnlineStoreConfig(
            connection_string=connection_string,
            key_ttl_seconds=self.feast_online_store_ttl,
        )

    @property
    def offline_config(self):
        if not FEAST_AVAILABLE:
            raise ImportError("Feast is not installed. Install with: uv sync --extra features")

        from modules.features.offline_store import RisingwaveOfflineStoreConfig

        from .kafka import KafkaConfig
        from .risingwave import RisingWaveConfig

        rw = RisingWaveConfig()
        kafka = KafkaConfig()

        return RisingwaveOfflineStoreConfig(
            host=rw.rw_host,
            port=rw.rw_port,
            database=rw.rw_name,
            user=rw.rw_user,
            password=rw.rw_pass.get_secret_value(),
            kafka_bootstrap_servers=kafka.kafka_bootstrap_servers,
        )
