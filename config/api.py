from .base import BaseConfig


class ApiConfig(BaseConfig):
    api_url: str
    api_prefix: str = "/api"
    api_docs_url: str = "/docs"
