
from faststream import FastStream
from faststream.confluent import KafkaBroker

from .core.embed import embedder
from .streaming.embeddings import TextEmbeddingsBatchHandler, AccountEmbeddingsEventHandler
from .modules.debezium import DebeziumEvent, process_debezium_batch, make_debezium_handler
from config import config

broker = KafkaBroker(config.kafka.kafka_bootstrap_servers)
app = FastStream(broker)

embeddings_publisher = broker.publisher('status_text_embeddings')

@broker.subscriber("status_texts", batch=True, max_records=config.embed.embed_max_batch_size)
async def on_status_texts(events: list[DebeziumEvent]):
    embeddings = await process_debezium_batch(
        events, 
        TextEmbeddingsBatchHandler, 
        args=(embedder, config.embed.embed_text_min_chars)
    )

    for item in embeddings:
        await embeddings_publisher.publish(item)
