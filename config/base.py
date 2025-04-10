
from pydantic_settings import BaseSettings

class BaseConfig(BaseSettings):
    class Config:
        env_file = ".env"
        extra = "ignore"
