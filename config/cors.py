
from .base import BaseConfig

class CorsConfig(BaseConfig):
    cors_origins: str | list[str] = '*'
    cors_credentials: bool = True

    @property
    def allow_origins(self):
        if type(self.cors_origins) == list:
            return self.cors_origins
        return self.cors_origins.split(',')

    @property
    def allow_credentials(self):
        return self.cors_credentials