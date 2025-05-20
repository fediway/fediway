from feast import FeatureStore
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from modules.schwarm import Schwarm

from .handlers.features import FeaturesEventHandler
from .handlers.schwarm import (
    StatusEventHandler as SchwarmStatusEventHandler,
    StatusStatsEventHandler as SchwarmStatusStatsEventHandler,
    FavouriteEventHandler as SchwarmFavouriteEventHandler,
    MentionEventHandler as SchwarmMentionEventHandler,
    StatusTagEventHandler as SchwarmStatusTagEventHandler,
)
from modules.debezium import (
    make_debezium_handler,
    DebeziumEvent,
    process_debezium_event,
)
from shared.core.feast import feature_store
from shared.core.qdrant import client
from shared.core.schwarm import driver
from config import config

broker = KafkaBroker(
    bootstrap_servers=config.kafka.kafka_bootstrap_servers,
)
app = FastStream(broker)

feature_topics = {
    "author_engagement_all_features",
    "author_engagement_is_favourite_features",
    "author_engagement_is_reblog_features",
    "author_engagement_is_reply_features",
    "author_engagement_has_image_features",
    "author_engagement_has_gifv_features",
    "author_engagement_has_video_features",
    "account_engagement_all_features",
    "account_engagement_is_favourite_features",
    "account_engagement_is_reblog_features",
    "account_engagement_is_reply_features",
    "account_engagement_has_image_features",
    "account_engagement_has_gifv_features",
    "account_engagement_has_video_features",
    "account_author_engagement_all_features",
    "account_author_engagement_is_favourite_features",
    "account_author_engagement_is_reblog_features",
    "account_author_engagement_is_reply_features",
    "account_author_engagement_has_image_features",
    "account_author_engagement_has_gifv_features",
    "account_author_engagement_has_video_features",
}

for topic in feature_topics:
    make_debezium_handler(
        broker,
        topic,
        FeaturesEventHandler,
        args=(feature_store, topic),
        group_id="features",
    )

# Schwarm consumers (responsible for pushing data to memgraph)


@broker.subscriber("statuses")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(
        event, SchwarmStatusEventHandler, args=(Schwarm(driver),)
    )


@broker.subscriber("mentions")
async def on_mentions(event: DebeziumEvent):
    await process_debezium_event(
        event, SchwarmMentionEventHandler, args=(Schwarm(driver),)
    )


@broker.subscriber("favourites")
async def on_favourites(event: DebeziumEvent):
    await process_debezium_event(
        event, SchwarmFavouriteEventHandler, args=(Schwarm(driver),)
    )


@broker.subscriber("statuses_tags")
async def on_statuses_tags(event: DebeziumEvent):
    await process_debezium_event(
        event, SchwarmStatusTagEventHandler, args=(Schwarm(driver),)
    )


@broker.subscriber("status_stats")
async def on_statuses_tags(event: DebeziumEvent):
    await process_debezium_event(
        event, SchwarmStatusStatsEventHandler, args=(Schwarm(driver),)
    )
