
from pydantic import BaseModel
from loguru import logger

class DebeziumPayload(BaseModel):
    op: str  # 'c', 'u', 'd', etc.
    before: dict | None
    after: dict | None
    source: dict

class DebeziumEvent(BaseModel):
    payload: DebeziumPayload

class DebeziumEventHandler:
    def parse(data):
        return data

    async def created(self, data: dict):
        pass

    async def updated(self, old: dict, new: dict):
        pass

    async def deleted(self, data: dict):
        pass

class DebeziumBatchHandler:
    def parse(data):
        return data

    async def created(self, data: list[dict]):
        pass

    async def updated(self, old: list[dict], new: list[dict]):
        pass

    async def deleted(self, data: list[dict]):
        pass

METHODS = {
    'c': 'created',
    'u': 'updated',
    'd': 'deleted',
}

async def process_debezium_event(event: DebeziumEvent, handler_cls, args):
    method = METHODS.get(event.payload.op)

    if method is None:
        logger.debug(f"Unhandled operation '{op}'.")
        return
    
    if not hasattr(handler_cls, method):
        logger.debug(f"Handler {handler_cls} does not handle '{method}'.")
        return

    if event.payload.op == 'u':
        callback_args = (handler_cls.parse(event.payload.before), handler_cls.parse(event.payload.after))
    elif event.payload.op in ['c', 'd']:
        callback_args = (handler_cls.parse(event.payload.after), )

    await getattr(handler_cls(*args), method)(*callback_args)

async def process_debezium_batch(events: list[DebeziumEvent], handler_cls, args):
    created_args = ([], )
    updated_args = ([], [])
    deleted_args = ([], )
    for event in events:
        if event.payload.op == 'u':
            updated_args[0].append(handler_cls.parse(event.payload.before))
            updated_args[1].append(handler_cls.parse(event.payload.after))
        elif event.payload.op == 'c':
            created_args[0].append(handler_cls.parse(event.payload.after))
        elif event.payload.op == 'd':
            deleted_args[0].append(handler_cls.parse(event.payload.after))

    handler = handler_cls(*args)

    results = []

    if len(created_args[0]) > 0 and hasattr(handler_cls, 'created'):
        result = await handler.created(*created_args)
        if result is not None:
            results += result
    if len(updated_args[0]) > 0 and hasattr(handler_cls, 'updated'):
        result = await handler.updated(*updated_args)
        if result is not None:
            results += result
    if len(deleted_args[0]) > 0 and hasattr(handler_cls, 'deleted'):
        result = await handler.deleted(*deleted_args)
        if result is not None:
            results += result

    return results

def make_debezium_handler(broker, topic: str, event_handler, args):
    @broker.subscriber(topic)
    async def _handler(event: DebeziumEvent):
        logger.debug(f"Consuming debezium event {topic}.")
        await process_debezium_event(event, event_handler, args=args)
    return _handler