
from sentence_transformers import SentenceTransformer

from app.modules.embed import SentenceTransformerEmbedder
from config import config

text_embeder = SentenceTransformerEmbedder(config.embed.sentence_transformer)
