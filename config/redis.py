from urllib.parse import quote

from .base import BaseConfig


class RedisConfig(BaseConfig):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_name: str | int = 0
    redis_pass: str | None = None
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0

    @property
    def url(self) -> str:
        encoded_pass = quote(self.redis_pass or "")
        return f"redis://:{encoded_pass}@{self.redis_host}:{self.redis_port}/{self.redis_name}"
