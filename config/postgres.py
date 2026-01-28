from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig


class PostgresConfig(BaseConfig):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "mastodon"
    db_pass: SecretStr = ""
    db_name: str = "mastodon_production"

    @property
    def url(self):
        return URL.create(
            "postgresql",
            username=self.db_user,
            password=self.db_pass.get_secret_value(),
            host=self.db_host,
            database=self.db_name,
            port=self.db_port,
        )
