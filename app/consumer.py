
from faststream import FastStream
from faststream.confluent import KafkaBroker
from pydantic import BaseModel
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
import app.utils as utils
from config import config

broker = KafkaBroker(config.db.kafka_url)
app = FastStream(broker)

class DebeziumPayload(BaseModel):
    op: str  # 'c', 'u', 'd', etc.
    before: dict | None
    after: dict | None
    source: dict

class DebeziumEvent(BaseModel):
    payload: DebeziumPayload

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

@broker.subscriber("postgres.public.accounts", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusEventHandler)

@broker.subscriber("postgres.public.statuses", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusEventHandler)

@broker.subscriber("postgres.public.mentions", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeMentionEventHandler)

@broker.subscriber("postgres.public.follows", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFollowEventHandler)

@broker.subscriber("postgres.public.favourites", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeFavouriteEventHandler)

@broker.subscriber("postgres.public.statuses_tags", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeStatusTagEventHandler)

@broker.subscriber("postgres.public.tags", conumser_group="herde")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, HerdeTagEventHandler)

# Feature consumer (responsible for pushing to feature store)

@broker.subscriber("postgres.public.statuses", conumser_group="features")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, FeaturesStatusEventHandler)

@broker.subscriber("postgres.public.favourites", conumser_group="features")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, FavouritesStatusEventHandler)

@broker.subscriber("postgres.public.follows", conumser_group="features")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, FavouritesStatusEventHandler)
