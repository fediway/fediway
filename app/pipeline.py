
from feast import FeatureStore
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from .events.features.account_author_features import AccountAuthorFeaturesEventHandler
from .modules.debezium import DebeziumEvent, process_debezium_event
from config import config

feature_store = FeatureStore(repo_path=config.feast.feast_repo_path)
broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

@broker.subscriber("account_author_features")
async def on_account_author_features(event: DebeziumEvent):
    await process_debezium_event(event, AccountAuthorFeaturesEventHandler, args=(feature_store, ))