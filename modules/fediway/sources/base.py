import json
from datetime import timedelta

from redis import Redis


class Source:
    def collect(self, limit: int, offset: int | None = None):
        raise NotImplemented

    def get_params(self):
        return {}

    def name(self):
        return str(type(self))


class RedisSource(Source):
    def __init__(self, r: Redis, ttl: timedelta):
        self.r = r
        self.ttl = ttl.seconds

    def compute(self):
        raise NotImplemented

    def redis_key(self):
        return "source:" + self.name()

    def reset(self):
        self.r.delete(self.redis_key())

    def store(self):
        candidates = [c for c in self.compute()]

        self.r.setex(self.redis_key(), self.ttl, json.dumps(candidates))

        return candidates

    def load(self):
        if not self.r.exists(self.redis_key()):
            candidates = self.store()
        else:
            candidates = json.loads(self.r.get(self.redis_key()))
        return candidates

    def collect(self, limit: int):
        return self.load()[:limit]
