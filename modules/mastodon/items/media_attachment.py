from ..models import MediaAttachment
from .base import Item

MEDIA_TYPES = {
    0: "image",
    1: "gifv",
    2: "audio",
    3: "unknown",
    4: "video",
}


class MediaAttachmentItem(Item):
    id: str
    type: str
    url: str | None
    preview_url: str | None
    remote_url: str | None
    meta: dict | None
    description: str | None
    blurhash: str | None

    @classmethod
    def from_model(cls, media_attachment: MediaAttachment):
        return cls(
            id=str(media_attachment.id),
            type=MEDIA_TYPES[media_attachment.type],
            url=media_attachment.file_url,
            preview_url=media_attachment.preview_url,
            remote_url=media_attachment.remote_url,
            meta=media_attachment.file_meta,
            description=media_attachment.description,
            blurhash=media_attachment.blurhash,
        )
