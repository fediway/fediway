from enum import Enum
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

from .base import BaseConfig


class EmbedConfig(BaseConfig):
    sentence_transformer: str = "sentence-transformers/LaBSE"

    clip_model: str = "M-CLIP/LABSE-Vit-L-14"
    clip_enabled: bool = False

    models_cache_dir: str = "data"

    embed_max_batch_size: int = 16
    embed_text_min_chars: int = 4

    k_latest_account_favourites_embeddings: int = 50
    k_latest_account_reblogs_embeddings: int = 50
    k_latest_account_replies_embeddings: int = 30
