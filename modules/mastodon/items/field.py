from datetime import datetime

from .base import Item


class FieldItem(Item):
    name: str
    value: str
    verified_at: datetime | None = None
