
import os
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

class FeastConfig(BaseConfig):
    feast_repo_path: str = "features"
    offline_store_path: str = "data/features"