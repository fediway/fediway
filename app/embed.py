
from faststream import FastStream
from faststream.confluent import KafkaBroker

from .core.embed import text_embeder
from .stream.embeddings import TextEmbeddingsEventHandler
from .modules.debezium import DebeziumEvent, process_debezium_batch
from config import config

broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

embeddings_publisher = broker.publisher('status_text_embeddings')

@broker.subscriber("status_texts", batch=True, max_records=config.embed.text_embed_max_batch_size)
async def on_status_texts(events: list[DebeziumEvent]):
    embeddings = await process_debezium_batch(events, TextEmbeddingsEventHandler, args=(text_embeder, ))
    for item in embeddings:
        await embeddings_publisher.publish(item)