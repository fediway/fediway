
import typer

from config import config

app = typer.Typer(help="Kafka commands.")

TOPICS = [
    NewTopic(
        "status_text_embeddings", 
        num_partitions=config.kafka.kafka_num_partitions, 
        replication_factor=config.kafka.kafka_replication_factor
    )
]

@app.command("create-topics")
def create_topics():
    from confluent_kafka.admin import AdminClient, NewTopic
    from confluent_kafka import KafkaException
    import asyncio

    admin = AdminClient({'bootstrap.servers': config.kafka.kafka_bootstrap_servers})
    existing_topics = admin.list_topics().topics.keys()

    topics = [topic for topic in TOPICS if topic.topic not in existing_topics]

    if len(topics) == 0:
        typer.echo("No topics to create.")
        return 0

    futures = admin.create_topics(TOPICS)

    # Wait for results (blocking call)
    for topic, future in futures.items():
        try:
            future.result()
            typer.echo(f"✅ Topic '{topic}' created")
        except KafkaException as e:
            typer.error(f"Topic creation failed: {e}")