from faststream import FastStream
from faststream.confluent import KafkaBroker

from config import config
from modules.debezium import (
    DebeziumEvent,
    make_debezium_handler,
    process_debezium_event,
)
from modules.schwarm import Schwarm
from shared.core.feast import feature_store
from shared.core.schwarm import driver

from .handlers.features import FeaturesEventHandler
from .handlers.schwarm import (
    FavouriteEventHandler as SchwarmFavouriteEventHandler,
)
from .handlers.schwarm import (
    MentionEventHandler as SchwarmMentionEventHandler,
)
from .handlers.schwarm import (
    StatusEventHandler as SchwarmStatusEventHandler,
)
from .handlers.schwarm import (
    StatusStatsEventHandler as SchwarmStatusStatsEventHandler,
)
from .handlers.schwarm import (
    StatusTagEventHandler as SchwarmStatusTagEventHandler,
)
from .utils import make_handler

broker = KafkaBroker(
    bootstrap_servers=config.kafka.kafka_bootstrap_servers,
)
app = FastStream(broker)

feature_topics = {
    "author_engagement_all",
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
    make_handler(
        broker, 
        "account_engagement_all_56d", 
        FeaturesEventHandler(feature_store, "account_engagement_all_56d"),
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
