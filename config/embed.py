
from enum import Enum
from pydantic import PostgresDsn, SecretStr, HttpUrl, RedisDsn

from .base import BaseConfig

class EmbedConfig(BaseConfig):
    sentence_transformer: str = 'sentence-transformers/all-MiniLM-L6-v2'
    
    clip_model: str = 'M-CLIP/LABSE-Vit-L-14'
    clip_enabled: bool = False

    models_cache_dir: str = 'data'

    embed_max_batch_size: int = 16
    embed_text_min_chars: int = 4

    k_latest_account_favourites_embeddings: int = 50
    k_latest_account_reblogs_embeddings: int = 50
    k_latest_account_replies_embeddings: int = 30

    @property
    def model_id(self):
        if self.clip_enabled:
            return self.clip_model
        return self.sentence_transformer

    @property
    def dim(self):
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(self.model_id, cache_dir=f"{self.models_cache_dir}/{self.model_id}")
        if self.clip_enabled:
            return config.numDims
        return config.hidden_size
