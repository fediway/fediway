
from pydantic import BaseModel
from loguru import logger

class DebeziumPayload(BaseModel):
    op: str  # 'c', 'u', 'd', etc.
    before: dict | None
    after: dict | None
    source: dict

class DebeziumEvent(BaseModel):
    payload: DebeziumPayload

async def process_debezium_event(event: DebeziumEvent, handler, args):
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
        callback_args = (handler.parse(event.payload.before), handler.parse(event.payload.after))
    elif event.payload.op in ['c', 'd']:
        callback_args = (handler.parse(event.payload.after), )

    await getattr(handler(*args), method)(*callback_args)

def make_debezium_handler(broker, topic: str, event_handler, args):
    @broker.subscriber(topic)
    async def _handler(event: DebeziumEvent):
        logger.debug(f"Consuming debezium event {topic}.")
        await process_debezium_event(event, event_handler, args=args)
    return _handler