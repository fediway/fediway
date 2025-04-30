
from qdrant_client import QdrantClient

from config import config

client = QdrantClient(host=config.qdrant.qdrant_host, port=config.qdrant.qdrant_port)