
from .base import BaseConfig

from pydantic import SecretStr

class DBConfig(BaseConfig):
    db_host: str       = "localhost"
    db_port: int       = 5432
    db_user: str       = "mastodon"
    db_pass: SecretStr = ""
    db_name: str       = "mastodon_development"