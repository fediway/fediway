
from feast import FeatureView, Field, FileSource, KafkaSource, FeatureService
from feast.data_format import JsonFormat
from feast.types import Int64
from datetime import timedelta

from entities import account, author
from data_sources import account_author_push_source


# Kafka Stream Source with Batch Source for Offline Store
# account_author_source = KafkaSource(
#     name="account_author_kafka",
#     timestamp_field="window_end",
#     kafka_bootstrap_servers="kafka_server:9092",
#     topic="account_author_features",
#     batch_source=batch_source,
#     message_format=JsonFormat(
#         schema_json="""
#         account_id integer, 
#         author_id integer, 
#         window_end timestamp, 
#         fav_count_7d integer, 
#         fav_count30d integer
#         """
#     ),
#     watermark_delay_threshold=timedelta(minutes=5),  # Latency threshold
# )


account_author_view = FeatureView(
    name="account_author_features",
    entities=[account, author],
    ttl=timedelta(days=365),
    schema=[
        Field(name="fav_count_7d", dtype=Int64),
        Field(name="reblogs_count_7d", dtype=Int64),
        Field(name="replies_count_7d", dtype=Int64),
        Field(name="fav_count_30d", dtype=Int64),
        Field(name="reblogs_count_30d", dtype=Int64),
        Field(name="replies_count_30d", dtype=Int64),
    ],
    online=True, 
    source=account_author_push_source
)