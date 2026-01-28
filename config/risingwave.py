from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig


class RisingWaveConfig(BaseConfig):
    rw_host: str = "localhost"
    rw_port: int = 4566
    rw_user: str = "root"
    rw_pass: SecretStr = ""
    rw_name: str = "dev"

    rw_migrations_paths: list[str] = ["migrations/risingwave"]
    rw_migrations_table: str = "migrations"

    rw_cdc_host: str | None = None
    rw_cdc_user: str = "risingwave"
    rw_cdc_pass: SecretStr = "password"

    rw_kafka_bootstrap_servers: str = "localhost:9092"

    @property
    def url(self):
        return URL.create(
            "postgresql",
            username=self.rw_user,
            password=self.rw_pass.get_secret_value(),
            host=self.rw_host,
            database=self.rw_name,
            port=self.rw_port,
        )
