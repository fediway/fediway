
from faststream import FastStream
from faststream.confluent import KafkaBroker

from .core.qdrant import client
from .core.embed import text_embeder
from .stream.embeddings import TextEmbeddingsEventHandler, AccountEmbeddingsEventHandler
from .modules.debezium import DebeziumEvent, process_debezium_batch, make_debezium_handler
from config import config

broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

embeddings_publisher = broker.publisher('status_text_embeddings')

@broker.subscriber("status_texts", batch=True, max_records=config.embed.text_embed_max_batch_size)
async def on_status_texts(events: list[DebeziumEvent]):
    embeddings = await process_debezium_batch(events, TextEmbeddingsEventHandler, args=(text_embeder, ))
    for item in embeddings:
        await embeddings_publisher.publish(item)

account_embedding_topics = [
    'latest_account_favourites_embeddings',
    'latest_account_reblogs_embeddings',
    'latest_account_replies_embeddings',
]

for topic in account_embedding_topics:
    make_debezium_handler(
        broker, topic, 
        AccountEmbeddingsEventHandler, 
        args=(client, topic)
    )
