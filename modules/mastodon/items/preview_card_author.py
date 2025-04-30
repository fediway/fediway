
from .base import Item
from .account import AccountItem

class PreviewCardAuthorItem(Item):
    name: str
    url: str
    account: AccountItem | None