from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class BaseConfig(BaseSettings):
    model_config = ConfigDict(env_file=f".env", extra="ignore")
