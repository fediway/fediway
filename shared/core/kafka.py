from faststream.confluent import KafkaBroker

from config import config

broker = KafkaBroker(config.kafka.kafka_bootstrap_servers)
