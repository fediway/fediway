from ..models import Account
from .base import Item


class AccountItem(Item):
    """
    see: https://docs.joinmastodon.org/entities/Account/
    """

    id: str
    username: str
    acct: str
    url: str | None
    uri: str
    locked: bool = False
    bot: bool = False
    discoverable: bool | None
    display_name: str
    note: str
    avatar: str | None
    avatar_static: str | None
    header: str | None
    header_static: str | None
    statuses_count: int
    followers_count: int
    following_count: int
    fields: list[str] = []
    emojis: list[str] = []
    last_status_at: str | None

    @classmethod
    def from_model(cls, account: Account):
        return cls(
            id=str(account.id),
            username=account.username,
            acct=account.pretty_acct,
            url=account.url,
            uri=account.uri,
            display_name=account.display_name,
            note=account.note,
            locked=account.locked,
            bot=account.bot,
            group=account.group,
            discoverable=account.discoverable,
            avatar=account.avatar_url,
            avatar_static=account.avatar_static_url,
            header=account.header_url,
            header_static=account.header_static_url,
            statuses_count=account.stats.statuses_count,
            followers_count=account.stats.followers_count,
            following_count=account.stats.following_count,
            last_status_at=account.stats.last_status_at.date().isoformat(),
        )
