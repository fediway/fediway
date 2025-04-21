
class Embedder():
    def __init__(self):
        pass

    def __call__(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_id: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id)
        
    def __call__(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=False)

    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()

if __name__ == "__main__":
    model_id = 'sentence-transformers/all-MiniLM-L6-v2'
    embedder = SentenceTransformerEmbedder(model_id)
    print(f"Embedding dimension of {model_id}: {embedder.dim()}")