
from .app import AppConfig
from .db import DBConfig
from .session import SessionConfig

class config:
    app = AppConfig()
    db = DBConfig()
    session = SessionConfig()