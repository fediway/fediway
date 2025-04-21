
import app.utils as utils

class Embedder():
    def __init__(self):
        pass

    def __call__(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_id: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id)
        
    def __call__(self, texts: list[str]) -> list[list[float]]:
        with utils.duration("Generated text embeddings in {:.3f} seconds."):
            return self.model.encode(texts)