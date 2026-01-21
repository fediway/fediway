from datetime import datetime
from typing import Optional

from ..models import Status
from .account import AccountItem
from .base import Item
from .emoji import EmojiItem
from .media_attachment import MediaAttachmentItem
from .mention import MentionItem
from .preview_card import PreviewCardItem
from .tag import TagItem

STATUS_VISIBILITY = {
    0: "public",
    1: "unlisted",
    2: "private",
    3: "direct",
}


class StatusItem(Item):
    id: str
    uri: str | None
    url: str | None
    created_at: datetime
    content: str | None
    visibility: str
    language: str | None = None
    edited_at: datetime | None = None
    sensitive: bool
    spoiler_text: str | None
    account: AccountItem
    media_attachments: list[MediaAttachmentItem] = []
    mentions: list[MentionItem] = []
    tags: list[TagItem] = []
    emojis: list[EmojiItem] = []
    reblog: Optional["StatusItem"] = None
    reblogs_count: int
    favourites_count: int
    replies_count: int
    quotes_count: int
    card: PreviewCardItem | None

    @classmethod
    def from_model(cls, status: Status, with_reblog: bool = True):
        return cls(
            id=str(status.id),
            uri=status.uri,
            url=status.local_url,
            created_at=status.created_at,
            edited_at=status.edited_at,
            language=status.language,
            account=AccountItem.from_model(account=status.account),
            media_attachments=[
                MediaAttachmentItem.from_model(m) for m in status.media_attachments
            ],
            content=status.text,
            visibility=STATUS_VISIBILITY[status.visibility],
            sensitive=status.sensitive,
            spoiler_text=status.spoiler_text,
            reblog=StatusItem.from_model(status.reblog, with_reblog=False)
            if status.reblog and with_reblog
            else None,
            reblogs_count=status.stats.untrusted_reblogs_count if status.stats is not None else 0,
            favourites_count=status.stats.untrusted_favourites_count
            if status.stats is not None
            else 0,
            replies_count=status.stats.replies_count if status.stats is not None else 0,
            quotes_count=status.stats.quotes_count,
            card=PreviewCardItem.from_model(status.preview_card)
            if status.preview_card
            else None,
        )


StatusItem.model_rebuild()
