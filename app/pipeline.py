
from feast import FeatureStore
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from modules.fediway.sources.herde import Herde

from .stream.herde import (
    AccountEventHandler as HerdeAccountEventHandler,
    StatusEventHandler as HerdeStatusEventHandler,
    FavouriteEventHandler as HerdeFavouriteEventHandler,
    FollowEventHandler as HerdeFollowEventHandler,
    MentionEventHandler as HerdeMentionEventHandler,
    StatusTagEventHandler as HerdeStatusTagEventHandler,
    TagEventHandler as HerdeTagEventHandler,
)
from .stream.features import FeaturesEventHandler
from .modules.debezium import make_debezium_handler, DebeziumEvent, process_debezium_event
from core.fs import fs as feature_store
from .core.qdrant import client
from .core.herde import driver
from config import config

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
        args=(feature_store, topic),
        group_id="features"
    )

# Embedding conumers (responsible for pushing vectors to qdrant)

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

# Herde consumers (responsible for pushing data to memgraph)

@broker.subscriber("accounts")
async def on_accounts(event: DebeziumEvent):
    await process_debezium_event(event, HerdeAccountEventHandler, args=(Herde(driver), ))

@broker.subscriber("statuses")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusEventHandler, args=(Herde(driver), ))

@broker.subscriber("mentions")
async def on_mentions(event: DebeziumEvent):
    await process_debezium_event(event, HerdeMentionEventHandler, args=(Herde(driver), ))

@broker.subscriber("follows")
async def on_follows(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFollowEventHandler, args=(Herde(driver), ))

@broker.subscriber("favourites")
async def on_favourites(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFavouriteEventHandler, args=(Herde(driver), ))

@broker.subscriber("statuses_tags")
async def on_statuses_tags(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusTagEventHandler, args=(Herde(driver), ))

@broker.subscriber("tags")
async def on_tags(event: DebeziumEvent):
    await process_debezium_event(event, HerdeTagEventHandler, args=(Herde(driver), ))