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

from .handlers.features import FeaturesJsonEventHandler, FeaturesDebeziumEventHandler
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
    fv.name: (
        fv.tags["online_store"],
        fv.tags.get("online_store_format") or "json",
    )
    for fv in feature_store.list_feature_views()
    if "online_store" in fv.tags
}

for feature_view, (topic, format) in feature_topics.items():
    if format == "json":
        make_handler(
            broker,
            topic,
            FeaturesJsonEventHandler(feature_store, feature_view),
            group_id="feature_store",
        )
    else:
        make_debezium_handler(
            broker,
            topic,
            FeaturesDebeziumEventHandler,
            args=(feature_store, feature_view),
            group_id="feature_store",
        )


# Schwarm consumers (responsible for pushing data to memgraph)


# @broker.subscriber("statuses")
# async def on_status(event: DebeziumEvent):
#     await process_debezium_event(
#         event, SchwarmStatusEventHandler, args=(Schwarm(driver),)
#     )


# @broker.subscriber("mentions")
# async def on_mentions(event: DebeziumEvent):
#     await process_debezium_event(
#         event, SchwarmMentionEventHandler, args=(Schwarm(driver),)
#     )


# @broker.subscriber("favourites")
# async def on_favourites(event: DebeziumEvent):
#     await process_debezium_event(
#         event, SchwarmFavouriteEventHandler, args=(Schwarm(driver),)
#     )


# @broker.subscriber("statuses_tags")
# async def on_statuses_tags(event: DebeziumEvent):
#     await process_debezium_event(
#         event, SchwarmStatusTagEventHandler, args=(Schwarm(driver),)
#     )


# @broker.subscriber("status_stats")
# async def on_statuses_tags(event: DebeziumEvent):
#     await process_debezium_event(
#         event, SchwarmStatusStatsEventHandler, args=(Schwarm(driver),)
#     )
