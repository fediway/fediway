
from feast import FeatureStore
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from .events.features.features import FeaturesEventHandler
from .modules.debezium import DebeziumEvent, process_debezium_event
from config import config

feature_store = FeatureStore(repo_path=config.feast.feast_repo_path)
broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

feature_topics = {
    'author_features': [
        'author_engagement_all_features',
        'author_engagement_is_favourite_features',
        'author_engagement_is_reblog_features',
        'author_engagement_is_reply_features',
        'author_engagement_has_image_features',
        'author_engagement_has_gifv_features',
        'author_engagement_has_video_features',
    ]   
}

for fv, topics in feature_topics.items():
    for topic in topics:
        @broker.subscriber(topic)
        async def features(event: DebeziumEvent):
            await process_debezium_event(
                event, 
                FeaturesEventHandler, 
                args=(feature_store, fv, topic)
            )