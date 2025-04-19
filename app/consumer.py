
from faststream import FastStream
from faststream.confluent import KafkaBroker
from loguru import logger

from modules.fediway.sources.herde import Herde
from .events.herde import (
    AccountEventHandler as HerdeAccountEventHandler,
    StatusEventHandler as HerdeStatusEventHandler,
    FavouriteEventHandler as HerdeFavouriteEventHandler,
    FollowEventHandler as HerdeFollowEventHandler,
    MentionEventHandler as HerdeMentionEventHandler,
    StatusTagEventHandler as HerdeStatusTagEventHandler,
    TagEventHandler as HerdeTagEventHandler,
)
from .core.herde import driver
from .modules.debezium import DebeziumEvent
import app.utils as utils
from config import config

broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

def get_dependencies():
    return {
        'herde': Herde(driver)
    }

async def process_debezium_event(event: DebeziumEvent, handler):
    method = {
        'c': 'created',
        'u': 'updated',
        'd': 'deleted',
    }.get(event.payload.op)

    if method is None:
        logger.debug(f"Unhandled operation '{op}'.")
        return
    
    if not hasattr(handler, method):
        logger.debug(f"Handler {handler} does not handle '{method}'.")
        return

    if event.payload.op == 'u':
        args = (handler.parse(event.payload.before), handler.parse(event.payload.after))
    elif event.payload.op in ['c', 'd']:
        args = (handler.parse(event.payload.after), )

    await getattr(handler(**get_dependencies()), method)(*args)

# Herde consumer (responsible for pushing to memgraph)

@broker.subscriber(config.db.debezium_topic("accounts"), conumser_group="herde")
async def on_accounts(event: DebeziumEvent):
    await process_debezium_event(event, HerdeAccountEventHandler)

@broker.subscriber(config.db.debezium_topic("statuses"), conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusEventHandler)

@broker.subscriber(config.db.debezium_topic("mentions"), conumser_group="herde")
async def on_mentions(event: DebeziumEvent):
    await process_debezium_event(event, HerdeMentionEventHandler)

@broker.subscriber(config.db.debezium_topic("follows"), conumser_group="herde")
async def on_follows(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFollowEventHandler)

@broker.subscriber(config.db.debezium_topic("favourites"), conumser_group="herde")
async def on_favourites(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFavouriteEventHandler)

@broker.subscriber(config.db.debezium_topic("statuses_tags"), conumser_group="herde")
async def on_statuses_tags(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusTagEventHandler)

@broker.subscriber(config.db.debezium_topic("tags"), conumser_group="herde")
async def on_tags(event: DebeziumEvent):
    await process_debezium_event(event, HerdeTagEventHandler)