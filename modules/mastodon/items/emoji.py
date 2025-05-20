from .base import Item


class EmojiItem(Item):
    shortcode: str
    url: str
    static_url: str
    visible_in_picker: bool
    category: str | None = None
