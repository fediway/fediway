
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class DBConfig(BaseConfig):
    
    # --- Postgresql ---

    db_host: str       = "localhost"
    db_port: int       = 5432
    db_user: str       = "mastodon"
    db_pass: SecretStr = ""
    db_name: str       = "mastodon_production"

    # --- Rising Wave ---

    rw_host: str       = "localhost"
    rw_port: int       = 4566
    rw_user: str       = "root"
    rw_pass: SecretStr = ""
    rw_name: str       = "dev"

    rw_migrations_paths: list[str] = ['migrations/risingwave']
    rw_migrations_table: str = "migrations"

    rw_pg_host: str | None = None
    rw_pg_user: str        = "risingwave"
    rw_pg_pass: SecretStr  = "password"
    
    rw_kafka_bootstrap_servers: str  = "kafka:9092"

    @property
    def url(self):
        return URL.create(
            "postgresql",
            username=self.db_user,
            password=self.db_pass.get_secret_value(),
            host=self.db_host,
            database=self.db_name,
            port=self.db_port
        )

    @property
    def rw_url(self):
        return URL.create(
            "postgresql",
            username=self.rw_user,
            password=self.rw_pass.get_secret_value(),
            host=self.rw_host,
            database=self.rw_name,
            port=self.rw_port
        )