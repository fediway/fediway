
from enum import Enum
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

from .base import BaseConfig

class EmbedConfig(BaseConfig):
    sentence_transformer: str = 'sentence-transformers/all-MiniLM-L6-v2'
    text_embed_max_batch_size: int = 8

    k_latest_account_favourites_embeddings: int = 50
    k_latest_account_reblogs_embeddings: int = 50
    k_latest_account_replies_embeddings: int = 30