
def make_handler(
    broker, topic: str, event_handler, group_id: str | None = None
):
    @broker.subscriber(topic, group_id=group_id)
    async def _handler(event: dict):
        await event_handler(event)

    return _handler