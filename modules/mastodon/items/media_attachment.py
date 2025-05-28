from ..models import MediaAttachment
from .base import Item

MEDIA_TYPES = {
    0: "image",
    1: "givf",
    2: "audio",
    3: "unknown",
    4: "video",
}


class MediaAttachmentItem(Item):
    id: int
    type: str
    url: str
    meta: dict | None

    @classmethod
    def from_model(cls, media_attachment: MediaAttachment):
        return cls(
            id=media_attachment.id,
            type=MEDIA_TYPES[media_attachment.type],
            url=media_attachment.file_url,
            meta=media_attachment.file_meta,
        )
