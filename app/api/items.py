
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

from app.modules.models.media_attachment import MediaAttachment
from app.modules.models.status import Status, StatusStats
from app.modules.models.account import Account, AccountStats
from app.modules.models.preview_card import PreviewCard
from app.modules.models.topic import Topic

class Item(BaseModel):
    class Config:
        extra = 'ignore'
        use_enum_values = True

class TopicItem(Item):
    name: str
    display_name: str

    @classmethod
    def from_model(cls, topic: Topic):
        return cls(
            name=topic.name,
            display_name=topic.display_name,
        )

class AccountItem(Item):
    id: int
    username: str
    acct: str
    url: str | None
    display_name: str
    note: str
    avatar: str | None
    avatar_static: str | None
    header: str | None
    header_static: str | None
    statuses_count: int
    followers_count: int
    following_count: int

    @classmethod
    def from_model(cls, account: Account):
        return cls(
            id=account.id,
            username=account.username,
            acct=f"{account.username}@{account.domain}",
            url=account.url,
            display_name=account.display_name,
            note=account.note,
            avatar=account.avatar_url,
            avatar_static=account.avatar_static_url,
            header=account.header_url,
            header_static=account.header_static_url,
            statuses_count=account.stats.statuses_count,
            followers_count=account.stats.followers_count,
            following_count=account.stats.following_count,
        )

class StatusVisibility(Enum):
    PUBLIC = 0 # Visible to everyone, shown in public timelines.
    UNLISTED = 1 # Visible to public, but not included in public timelines.
    PRIVATE = 2 # Visible to followers only, and to any mentioned users.
    DIRECT = 3 # Visible only to mentioned users.

    def __str__(self):
        return self.name.lower()

class MediaAttachmentItem(Item):
    id: int
    type: str
    url: str
    meta: dict

    @classmethod
    def from_model(cls, media_attachment: MediaAttachment):
        return cls(
            id=media_attachment.id,
            type={
                0: 'image',
                1: 'givf',
                2: 'audio',
                3: 'unknown',
                4: 'video',
            }[media_attachment.type],
            url=media_attachment.file_url,
            meta=media_attachment.file_meta,
        )

class MentionItem(Item):
    id: int
    username: str
    url: str
    acct: str

class TagItem(Item):
    name: str
    url: str

class EmojiItem(Item):
    shortcode: str
    url: str
    static_url: str
    visible_in_picker: bool
    category: str | None = None

class PreviewCardItem(Item):
    url: str
    title: str
    description: str
    type: str
    author_name: str
    author_url: str
    provider_name: str
    provider_url: str
    html: str
    width: int
    height: int
    image: str | None
    embed_url: str | None
    blurhash: str | None

    @classmethod
    def from_model(cls, card: PreviewCard):
        return cls(
            url=card.url,
            title=card.title,
            description=card.description,
            type={
                0: 'link',
                1: 'photo',
                2: 'video',
                3: 'rich',
            }[card.type],
            author_name=card.author_name,
            author_url=card.author_url,
            provider_name=card.provider_name,
            provider_url=card.provider_url,
            html=card.html,
            width=card.width,
            height=card.height,
            image='',
            embed_url=card.embed_url,
            blurhash=card.blurhash,
        )

class StatusItem(Item):
    id: int
    uri: str
    url: str
    created_at: datetime
    content: str
    visibility: StatusVisibility
    sensitive: bool
    spoiler_text: str
    account: AccountItem
    media_attachments: list[MediaAttachmentItem] = []
    mentions: list[MentionItem] = []
    tags: list[TagItem] = []
    emojis: list[EmojiItem] = []
    reblog: Optional["StatusItem"] = None
    reblogs_count: int
    favourites_count: int
    replies_count: int
    card: PreviewCardItem | None

    @classmethod
    def from_model(cls, status: Status, with_reblog: bool = True):
        return cls(
            id=status.id,
            uri=status.uri,
            url=status.url,
            created_at=status.created_at,
            account=AccountItem.from_model(account=status.account),
            media_attachments=[MediaAttachmentItem.from_model(m) for m in status.media_attachments],
            content=status.text,
            visibility=StatusVisibility(status.visibility),
            sensitive=status.sensitive,
            spoiler_text=status.spoiler_text,
            reblog=StatusItem.from_model(status.reblog, with_reblog=False) if status.reblog and with_reblog else None,
            reblogs_count=status.stats.reblogs_count if status.stats is not None else 0,
            favourites_count=status.stats.favourites_count if status.stats is not None else 0,
            replies_count=status.stats.replies_count if status.stats is not None else 0,
            card=PreviewCardItem.from_model(status.preview_card) if status.preview_card else None
        )

StatusItem.model_rebuild()