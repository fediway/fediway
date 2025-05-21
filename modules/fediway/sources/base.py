import json
from datetime import timedelta

from redis import Redis


class Source:
    def collect(self, limit: int, offset: int | None = None):
        raise NotImplemented

    def __str__(self):
        return str(type(self))


class RedisSource(Source):
    def __init__(self, key: str, r: Redis, ttl: timedelta):
        self.r = r
        self.ttl = ttl.seconds
        self.key = key

    def compute(self):
        raise NotImplemented

    def store(self):
        candidates = self.compute()

        self.r.setex(self.key, self.ttl, json.dumps(candidates))

        return candidates

    def collect(self, limit: int):
        if not self.r.exists(self.key):
            return self.store()
        return json.loads(self.r.get(self.key))[:limit]
