import typer

from config import config

app = typer.Typer(help="Kafka commands.")


def _topic(topic):
    from confluent_kafka.admin import NewTopic

    return NewTopic(
        topic,
        num_partitions=config.kafka.kafka_num_partitions,
        replication_factor=config.kafka.kafka_replication_factor,
        # https://kafka.apache.org/documentation.html#topicconfigs
        config={
            "retention.ms": "60000",  # 1 minute
            "segment.ms": "300000",  # force frequent cleanup
        },
    )


TOPICS = [
    "status_text_embeddings",
    "feeds",
    "feed_pipeline_runs",
    "feed_pipeline_steps",
    "feed_sourcing_runs",
    "feed_recommendations",
    "feed_recommendation_sources",
    "feed_ranking_runs",
]


@app.command("create-topics")
def create_topics():
    from confluent_kafka import KafkaException
    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": config.kafka.kafka_bootstrap_servers})
    existing_topics = admin.list_topics().topics.keys()

    topics = [_topic(topic) for topic in TOPICS if topic not in existing_topics]

    if len(topics) == 0:
        typer.echo("No topics to create.")
        return 0

    futures = admin.create_topics(topics)

    # Wait for results (blocking call)
    for topic, future in futures.items():
        try:
            future.result()
            typer.echo(f"✅ Topic '{topic}' created")
        except KafkaException as e:
            typer.echo(f"Topic creation failed: {e}")
