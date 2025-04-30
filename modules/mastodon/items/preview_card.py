
from .base import Item
from ..models import PreviewCard

PREVIEW_CARD_TYPES = {
    0: 'link',
    1: 'photo',
    2: 'video',
    3: 'rich',
}

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
            type=PREVIEW_CARD_TYPES[card.type],
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