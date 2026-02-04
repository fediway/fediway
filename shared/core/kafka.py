import json

from config import config
from shared.utils import JSONEncoder

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None


def get_kafka_producer():
    if KafkaProducer is None:
        raise ImportError("kafka-python is not installed. Install with: uv sync --extra streaming")
    return KafkaProducer(
        bootstrap_servers=config.kafka.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, cls=JSONEncoder).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k else None,
        max_in_flight_requests_per_connection=5,
        acks=1,
        retries=3,
    )
