import typer

from config import config

app = typer.Typer(help="Feast commands.")


@app.command("apply")
def apply():
    from confluent_kafka import KafkaException
    from confluent_kafka.admin import AdminClient
    from feast import OnDemandFeatureView

    from features import ENTITIES, FEATURE_VIEWS, FEATURES_SERVICES
    from shared.core.feast import feature_store

    from .kafka import _topic

    feature_store.apply(ENTITIES)
    feature_store.apply(FEATURE_VIEWS)
    feature_store.apply(FEATURES_SERVICES)

    admin = AdminClient({"bootstrap.servers": config.kafka.kafka_bootstrap_servers})
    existing_topics = admin.list_topics().topics.keys()

    topics = []
    for fv in FEATURE_VIEWS:
        if isinstance(fv, OnDemandFeatureView):
            continue

        if fv.source.batch_source.table not in existing_topics:
            topics.append(_topic(fv.source.batch_source.table))

    if len(topics) > 0:
        futures = admin.create_topics(topics)

        for topic, future in futures.items():
            try:
                future.result()
                typer.echo(f"✅ Kafka topic '{topic}' created")
            except KafkaException as e:
                typer.echo(f"Topic creation failed: {e}")
