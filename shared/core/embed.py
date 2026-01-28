from config import config
from modules.fediway.embedding import ClipEmbedder, SentenceTransformerEmbedder


def get_embedder():
    if config.embed.clip_enabled:
        return ClipEmbedder(config.embed.clip_model, cache_dir=config.embed.models_cache_dir)

    return SentenceTransformerEmbedder(
        config.embed.sentence_transformer, cache_dir=config.embed.models_cache_dir
    )


embedder = get_embedder()
