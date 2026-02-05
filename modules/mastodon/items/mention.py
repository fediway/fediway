from .base import Item


class MentionItem(Item):
    id: str
    username: str
    url: str
    acct: str
