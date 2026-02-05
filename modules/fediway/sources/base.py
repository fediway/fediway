import json
from datetime import timedelta
from typing import ClassVar

from redis import Redis

from shared.utils.strings import camel_to_snake, humanize


class Source:
    _id: ClassVar[str | None] = None
    _display_name: ClassVar[str | None] = None
    _description: ClassVar[str | None] = None
    _tracked_params: ClassVar[list[str]] = []
    _skip_params_validation: ClassVar[bool] = False
    _default_fallback_threshold: ClassVar[float] = 0.5

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Only skip validation if THIS class explicitly sets _skip_params_validation
        if "_skip_params_validation" in cls.__dict__ and cls._skip_params_validation:
            return
        # Default to empty list if not defined
        if "_tracked_params" not in cls.__dict__:
            cls._tracked_params = []

    def fallback(self, source: "Source", threshold: float | None = None) -> "Source":
        self._fallback_source = source
        if threshold is not None:
            self._fallback_threshold_value = threshold
        return self

    def get_fallback(self) -> "Source | None":
        return getattr(self, "_fallback_source", None)

    @property
    def fallback_threshold(self) -> float:
        return getattr(self, "_fallback_threshold_value", self._default_fallback_threshold)

    def has_fallback(self) -> bool:
        return self.get_fallback() is not None

    @property
    def id(self) -> str:
        if self._id:
            return self._id
        return camel_to_snake(self.__class__.__name__)

    @property
    def display_name(self) -> str:
        if self._display_name:
            return self._display_name
        name = self.__class__.__name__
        for suffix in ("Source",):
            name = name.removesuffix(suffix)
        return humanize(camel_to_snake(name))

    @property
    def description(self) -> str | None:
        if self._description:
            return self._description
        if self.__doc__:
            return self.__doc__.strip().split("\n")[0]
        return None

    @property
    def class_path(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def get_params(self) -> dict:
        return {k: getattr(self, k) for k in self._tracked_params}

    def collect(self, limit: int, offset: int | None = None):
        raise NotImplementedError


class RedisSource(Source):
    _skip_params_validation = True

    def __init__(self, r: Redis, ttl: timedelta):
        self.r = r
        self.ttl = ttl.seconds

    def compute(self):
        raise NotImplementedError

    def redis_key(self):
        return "source:" + self.id

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
            raw = self.r.get(self.redis_key())
            try:
                candidates = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                self.r.delete(self.redis_key())
                candidates = self.store()
        return candidates

    def collect(self, limit: int):
        return self.load()[:limit]
