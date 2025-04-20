
from feast import FeatureStore
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from .events.features.features import FeaturesEventHandler
from .modules.debezium import make_debezium_handler
from config import config

feature_store = FeatureStore(repo_path=config.feast.feast_repo_path)
broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

feature_topics = {
    'author_engagement_all_features',
    'author_engagement_is_favourite_features',
    'author_engagement_is_reblog_features',
    'author_engagement_is_reply_features',
    'author_engagement_has_image_features',
    'author_engagement_has_gifv_features',
    'author_engagement_has_video_features',

    'account_engagement_all_features',
    'account_engagement_is_favourite_features',
    'account_engagement_is_reblog_features',
    'account_engagement_is_reply_features',
    'account_engagement_has_image_features',
    'account_engagement_has_gifv_features',
    'account_engagement_has_video_features',

    'account_author_engagement_all_features',
    'account_author_engagement_is_favourite_features',
    'account_author_engagement_is_reblog_features',
    'account_author_engagement_is_reply_features',
    'account_author_engagement_has_image_features',
    'account_author_engagement_has_gifv_features',
    'account_author_engagement_has_video_features',
}

for topic in feature_topics:
    make_debezium_handler(
        broker, topic, 
        FeaturesEventHandler, 
        args=(feature_store, topic)
    )
