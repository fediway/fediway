
from redis import Redis

from .base import Source

class MastodonStatusTrendSource(Source):
    def __init__(self, redis):
        self.r = redis

    def collect(self, limit: int):
        raise NotImplementedError

        return self.r.smembers(self.r.keys('trending_statuses:used*')[0])[:limit]