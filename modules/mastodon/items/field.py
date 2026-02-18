from .base import Item, UTCDatetime


class FieldItem(Item):
    """see: https://docs.joinmastodon.org/entities/Field/"""

    name: str
    value: str
    verified_at: UTCDatetime | None = None
