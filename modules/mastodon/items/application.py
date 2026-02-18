from .base import Item


class ApplicationItem(Item):
    """see: https://docs.joinmastodon.org/entities/Application/"""

    name: str
    website: str | None = None
