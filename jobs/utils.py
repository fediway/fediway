
from bs4 import BeautifulSoup
from collections import OrderedDict
import re

class FixedSizeSet:
    """A set-like cache that evicts the oldest item when full."""
    def __init__(self, maxlen=1000):
        self.maxlen = maxlen
        self._cache = OrderedDict()

    def add(self, item):
        if item in self._cache:
            # Move to end to mark as recently used
            self._cache.move_to_end(item)
        else:
            # Add new item and evict oldest if full
            self._cache[item] = None
            if len(self._cache) > self.maxlen:
                self._cache.popitem(last=False)

    def __contains__(self, item):
        return item in self._cache

    def __len__(self):
        return len(self._cache)

    def __repr__(self):
        return f"FixedSizeSet({list(self._cache.keys())})"

def strip_html(html):
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)

def strip_emojis(text):
    emoji = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f" # dingbats
        u"\u3030"
                        "]+", re.UNICODE)
    return re.sub(emoji, '', text)

def strip_special_chars(text: str) -> str:
    """Remove special characters but preserve Unicode letters and some punctuation."""
    return re.sub(r"[^\w\s.,!?\-']", "", text, flags=re.UNICODE)

def strip_links(text: str) -> str:
    """Remove all URLs, including those starting with www."""
    return " ".join([word for word in text.split() if not 'http' in word and not 'www' in word])
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"
    )
    return url_pattern.sub("", text)