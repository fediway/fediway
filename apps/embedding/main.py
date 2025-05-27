from faststream import FastStream
from faststream.confluent import KafkaBroker

from config import config
from modules.debezium import (
    DebeziumEvent,
    process_debezium_batch,
)
from shared.core.embed import embedder

from .handlers.embeddings import (
    TextEmbeddingsBatchHandler,
)

broker = KafkaBroker(config.kafka.kafka_bootstrap_servers)
app = FastStream(broker)

handler = TextEmbeddingsBatchHandler(embedder, config.embed.embed_text_min_chars)


@broker.subscriber(
    "status_texts", batch=True, max_records=config.embed.embed_max_batch_size
)
async def on_status_texts(events: list[dict]):
    handler(events)
