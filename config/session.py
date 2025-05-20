from .base import BaseConfig

from pydantic import SecretStr


class SessionConfig(BaseConfig):
    session_max_size: int = 10_000
    session_ttl: int = 6_000
    session_cookie_name: str = "fediway_session_id"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_name: str | int = 0
    redis_pass: str | None = None
