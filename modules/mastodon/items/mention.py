from .base import Item


class MentionItem(Item):
    """see: https://docs.joinmastodon.org/entities/Status/#Mention"""

    id: str
    username: str
    url: str
    acct: str
