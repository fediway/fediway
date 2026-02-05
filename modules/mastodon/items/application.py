from .base import Item


class ApplicationItem(Item):
    name: str
    website: str | None = None
