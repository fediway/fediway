
from .base import BaseConfig

from pydantic import SecretStr

class SessionConfig(BaseConfig):
    session_max_size: int           = 10_000
    session_max_age_in_seconds: int = 6_000
    session_cookie_name: str        = 'fediway_session_id'