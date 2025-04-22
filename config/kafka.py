
from pydantic import SecretStr

from .base import BaseConfig

class KafkaConfig(BaseConfig):
    kafka_bootstrap_servers: str = "localhost:29092"
    kafka_num_partitions: int = 1
    kafka_replication_factor: int = 1

    kafka_user: str = ''
    kafka_pass: SecretStr = ''

    @property
    def faststream_security():
        from faststream.security import SASLPlaintext

        return None

        return SASLPlaintext(
            username=self.kafka_user, 
            password=self.kafka_pass.get_secret_value()
        )