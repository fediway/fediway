from urllib.parse import quote

from .base import BaseConfig


class RedisConfig(BaseConfig):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_name: str | int = 0
    redis_pass: str | None = None

    @property
    def url(self) -> str:
        encoded_pass = quote(self.redis_pass or "")
        return f"redis://:{encoded_pass}@{self.redis_host}:{self.redis_port}/{self.redis_name}"
