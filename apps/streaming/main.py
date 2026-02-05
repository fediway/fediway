from faststream import FastStream
from faststream.confluent import KafkaBroker

from config import config
from modules.debezium import (
    make_debezium_handler,
)
from shared.core.feast import feature_store

from .handlers.features import FeaturesDebeziumEventHandler, FeaturesJsonEventHandler
from .utils import make_handler

broker = KafkaBroker(
    bootstrap_servers=config.kafka.kafka_bootstrap_servers,
)
app = FastStream(broker)

feature_topics = {
    fv.name: (
        fv.tags["online_store"],
        fv.tags.get("online_store_format") or "json",
    )
    for fv in feature_store.list_feature_views()
    if "online_store" in fv.tags
}

for feature_view, (topic, format) in feature_topics.items():
    if format == "json":
        make_handler(
            broker,
            topic,
            FeaturesJsonEventHandler(feature_store, feature_view),
            group_id="feature_store",
        )
    else:
        make_debezium_handler(
            broker,
            topic,
            FeaturesDebeziumEventHandler,
            args=(feature_store, feature_view),
            group_id="feature_store",
        )
