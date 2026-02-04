from datetime import datetime

from ..models import Account
from .base import Item
from .field import FieldItem


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
    group: bool = False
    discoverable: bool | None
    indexable: bool = False
    display_name: str
    note: str
    avatar: str | None
    avatar_static: str | None
    header: str | None
    header_static: str | None
    statuses_count: int
    followers_count: int
    following_count: int
    created_at: datetime
    fields: list[FieldItem] = []
    emojis: list = []
    last_status_at: str | None

    @classmethod
    def from_model(cls, account: Account):
        last_status_at = account.stats.last_status_at
        if last_status_at is not None:
            last_status_at = last_status_at.date().isoformat()

        # Mastodon returns created_at as midnight of the creation date
        created_at = account.created_at
        if created_at is not None:
            created_at = created_at.replace(hour=0, minute=0, second=0, microsecond=0)

        fields = []
        if account.fields:
            for field in account.fields:
                fields.append(
                    FieldItem(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        verified_at=field.get("verified_at"),
                    )
                )

        return cls(
            id=str(account.id),
            username=account.username,
            acct=account.pretty_acct,
            url=account.local_url,
            uri=account.local_uri,
            display_name=account.display_name,
            note=account.note,
            locked=account.locked,
            bot=account.bot,
            group=account.group,
            discoverable=account.discoverable,
            indexable=account.indexable,
            avatar=account.avatar_url,
            avatar_static=account.avatar_static_url,
            header=account.header_url,
            header_static=account.header_static_url,
            statuses_count=account.stats.statuses_count,
            followers_count=account.stats.followers_count,
            following_count=account.stats.following_count,
            created_at=created_at,
            fields=fields,
            last_status_at=last_status_at,
        )
