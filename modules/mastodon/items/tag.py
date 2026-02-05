from config import config

from ..models import Tag
from .base import Item


class TagItem(Item):
    id: str
    name: str
    url: str
    history: list = []

    @classmethod
    def from_model(cls, tag: Tag):
        # Use display_name if available (preserves case), otherwise name
        name = tag.display_name if tag.display_name else tag.name
        return cls(
            id=str(tag.id),
            name=name,
            url=f"https://{config.app.app_host}/tags/{tag.name}",
            history=[],
        )
