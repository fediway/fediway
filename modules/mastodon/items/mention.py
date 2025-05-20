from .base import Item
from ..models import Mention


class MentionItem(Item):
    id: int
    username: str
    url: str
    acct: str
