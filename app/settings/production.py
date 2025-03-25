
from .base import AppSettings

class ProdAppSettings(AppSettings):
    class Config(AppSettings.Config):
        env_file = "prod.env"

    @property
    def fastapi_kwargs(self) -> dict[str, any]:
        return {
            "debug": self.debug,
            "title": self.title,
            "version": self.version,
        }