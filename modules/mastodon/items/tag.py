from .base import Item
from ..models import Tag


class TagItem(Item):
    name: str
    url: str

    # @classmethod
    # def from_model(cls, tag: Tag):
    #     return cls(
    #         name=tag.name,
    #         url=tag.url
    #     )
