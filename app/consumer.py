
from faststream import FastStream
from faststream.confluent import KafkaBroker
from pydantic import BaseModel
from loguru import logger

from modules.fediway.sources.herde import Herde
from .events import (
    AccountEventHandler,
    StatusEventHandler,
    FavouriteEventHandler,
    FollowEventHandler,
    MentionEventHandler,
    StatusTagEventHandler,
    TagEventHandler,
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

@broker.subscriber("postgres.public.accounts")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, StatusEventHandler)

@broker.subscriber("postgres.public.statuses")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, StatusEventHandler)

@broker.subscriber("postgres.public.mentions")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, MentionEventHandler)

@broker.subscriber("postgres.public.follows")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, FollowEventHandler)

@broker.subscriber("postgres.public.favourites")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, FavouriteEventHandler)

@broker.subscriber("postgres.public.statuses_tags")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, StatusTagEventHandler)

@broker.subscriber("postgres.public.tags")
async def on_status(event: DebeziumEvent):
    await process_debezium_event(event, TagEventHandler)