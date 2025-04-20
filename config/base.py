
import os
import logging
from pydantic_settings import BaseSettings

class BaseConfig(BaseSettings):
    class Config:
        env_file = f".env"
        extra = "ignore"