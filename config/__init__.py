
from .api import ApiConfig
from .app import AppConfig
from .cors import CorsConfig
from .db import DBConfig
from .feed import FeedConfig
from .files import FilesConfig
from .geo import GeoLocationConfig
from .logging import LoggingConfig
from .session import SessionConfig

class classproperty(property):
    def __get__(self, obj, cls):
        return self.fget(cls)

class config:
    api = ApiConfig()
    app = AppConfig()
    cors = CorsConfig()
    db = DBConfig()
    feed = FeedConfig()
    files = FilesConfig()
    geo = GeoLocationConfig()
    logging = LoggingConfig()
    session = SessionConfig()

    @classproperty
    def fastapi_kwargs(cls) -> dict[str, any]:
        return {
            "docs_url": cls.api.api_docs_url,
            "debug": cls.app.debug,
            "title": cls.app.app_title,
            "version": cls.app.app_version,
        }