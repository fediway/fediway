from .base import Embedder


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_id: str, cache_dir: str = "data"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id, cache_folder=f"{cache_dir}/{model_id}")

    def __call__(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=False)

    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()


if __name__ == "__main__":
    texts = [
        "Three blind horses listening to Mozart.",
        "Älgen är skogens konung!",
        "Wie leben Eisbären in der Antarktis?",
        "Вы знали, что все белые медведи левши?",
    ]

    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    embedder = SentenceTransformerEmbedder(model_id)
    print(f"Embedding dimension of {model_id}: {embedder.dim()}")
    import time

    import torch

    torch.set_num_threads(4)

    for _ in range(10):
        start = time.time()
        embeddings = embedder(texts)
        print(f"Generated embeddings in {time.time() - start} seconds.")
