
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class DBConfig(BaseConfig):
    db_host: str       = "localhost"
    db_port: int       = 5432
    db_user: str       = "mastodon"
    db_pass: SecretStr = ""
    db_name: str       = "mastodon_production"

    kafka_host: str       = "localhost"
    kafka_port: int       = 29092
    kafka_user: str       = ""
    kafka_pass: SecretStr = ""

    debezium_db_host: str = 'postgres'
    debezium_host: str = 'localhost'
    debezium_port: int = 8083
    debezium_connector_name: str = "postgres-connector"
    debezium_db_server: str = "pgserver"
    debezium_topic_prefix: str = "postgres"
    debezium_tables: list[str] = [
        'accounts', 
        'statuses',
        'status_stats',
        'follows',
        'mentions',
        'favourites',
        'tags',
        'statuses_tags',
    ]

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
    def kafka_url(self) -> str:
        return f"{self.kafka_host}:{self.kafka_port}"

    @property
    def debezium_url(self):
        return f"http://{self.debezium_host}:{self.debezium_port}"

    @property
    def debezium_connector_config(self):
        return {
            "name": self.debezium_connector_name,
            "config": {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "topic.prefix": self.debezium_topic_prefix,
                "plugin.name": "pgoutput",
                "database.hostname": "postgres",
                "database.port": self.db_port,
                "database.user": self.db_user,
                "database.password": self.db_pass.get_secret_value(),
                "database.dbname": self.db_name,
                "database.server.name": self.debezium_db_server,
                "table.include.list": ",".join([f"public.{table}" for table in self.debezium_tables]),
                "key.converter": "org.apache.kafka.connect.json.JsonConverter",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "topic.creation.default.replication.factor": 1,
                "topic.creation.default.partitions": 1,
                "topic.creation.enable": True
            }
        }