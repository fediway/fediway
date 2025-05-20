from .base import BaseConfig


class QdrantConfig(BaseConfig):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
