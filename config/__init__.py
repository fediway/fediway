
from .api import ApiConfig
from .app import AppConfig
from .cors import CorsConfig
from .db import DBConfig
from .embed import EmbedConfig
from .feast import FeastConfig
from .fediway import FediwayConfig
from .files import FilesConfig
from .geo import GeoLocationConfig
from .logging import LoggingConfig
from .session import SessionConfig
from .tasks import TasksConfig

class classproperty(property):
    def __get__(self, obj, cls):
        return self.fget(cls)

class config:
    api = ApiConfig()
    app = AppConfig()
    cors = CorsConfig()
    db = DBConfig()
    embed = EmbedConfig()
    feast = FeastConfig()
    fediway = FediwayConfig()
    files = FilesConfig()
    geo = GeoLocationConfig()
    logging = LoggingConfig()
    session = SessionConfig()
    tasks = TasksConfig()

    @classproperty
    def fastapi_kwargs(cls) -> dict[str, any]:
        return {
            "docs_url": cls.api.api_docs_url,
            "debug": cls.app.debug,
            "title": cls.app.app_title,
            "version": cls.app.app_version,
        }