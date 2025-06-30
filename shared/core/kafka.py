from kafka import KafkaProducer
import json

import modules.utils as utils
from config import config


def get_kafka_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=config.kafka.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, cls=utils.JSONEncoder).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k else None,
        max_in_flight_requests_per_connection=5,
        acks=1,
        retries=3,
    )
