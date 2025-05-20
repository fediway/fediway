from .base import Item


class MentionItem(Item):
    id: int
    username: str
    url: str
    acct: str
