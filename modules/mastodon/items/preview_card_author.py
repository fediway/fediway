from .account import AccountItem
from .base import Item


class PreviewCardAuthorItem(Item):
    """see: https://docs.joinmastodon.org/entities/PreviewCard/#authors"""

    name: str
    url: str
    account: AccountItem | None
