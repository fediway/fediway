
from pydantic import SecretStr

from .base import BaseConfig

class KafkaConfig(BaseConfig):
    kafka_bootstrap_servers: str = "localhost:29092"
    kafka_num_partitions: int = 1
    kafka_replication_factor: int = 1