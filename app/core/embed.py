
from app.modules.embed import SentenceTransformerEmbedder, ClipEmbedder
from config import config

def get_embedder():
    if config.embed.clip_enabled:
        return ClipEmbedder(config.embed.clip_model)

    return SentenceTransformerEmbedder(config.embed.sentence_transformer)

embedder = get_embedder()

