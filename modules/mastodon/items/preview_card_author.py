from .account import AccountItem
from .base import Item


class PreviewCardAuthorItem(Item):
    name: str
    url: str
    account: AccountItem | None
