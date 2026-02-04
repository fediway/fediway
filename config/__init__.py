from .api import ApiConfig
from .app import AppConfig
from .base import BaseConfig, FilesConfig, TasksConfig
from .cors import CorsConfig
from .embed import EmbedConfig
from .feast import FeastConfig
from .fediway import FediwayConfig
from .geo import GeoLocationConfig
from .kafka import KafkaConfig
from .logging import LoggingConfig
from .postgres import PostgresConfig
from .qdrant import QdrantConfig
from .redis import RedisConfig
from .risingwave import RisingWaveConfig
from .sources import SourceConfig, SourcesConfig


class classproperty(property):
    def __get__(self, obj, cls):
        return self.fget(cls)


class config:
    api = ApiConfig()
    app = AppConfig()
    cors = CorsConfig()
    embed = EmbedConfig()
    feast = FeastConfig()
    fediway = FediwayConfig()
    files = FilesConfig()
    geo = GeoLocationConfig()
    kafka = KafkaConfig()
    logging = LoggingConfig()
    postgres = PostgresConfig()
    qdrant = QdrantConfig()
    redis = RedisConfig()
    risingwave = RisingWaveConfig()
    tasks = TasksConfig()

    # Backward compatibility aliases
    db = postgres  # Old code may use config.db

    @classproperty
    def fastapi_kwargs(cls) -> dict[str, any]:
        return {
            "docs_url": cls.api.api_docs_url,
            "debug": cls.app.debug,
            "title": cls.app.app_title,
            "version": cls.app.app_version,
        }
