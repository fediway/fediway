from .base import Item


class EmojiItem(Item):
    """see: https://docs.joinmastodon.org/entities/CustomEmoji/"""

    shortcode: str
    url: str
    static_url: str
    visible_in_picker: bool
    category: str | None = None
