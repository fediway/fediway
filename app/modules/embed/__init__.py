
class Embedder():
    def __init__(self):
        pass

    def __call__(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError

class MultimodalEmbedder():
    def __init__(self):
        pass

    def texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_id: str, cache_dir: str = 'data'):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id, cache_dir=f"{cache_dir}/{model_id}", local_files_only=True)
        
    def __call__(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=False)

    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()

class ClipEmbedder(MultimodalEmbedder):
    def __init__(self, model_id: str, cache_dir: str = 'data'):
        from multilingual_clip import pt_multilingual_clip
        import transformers

        self.model = pt_multilingual_clip.MultilingualCLIP.from_pretrained(model_id, cache_dir=f"{cache_dir}/{model_id}", local_files_only=True)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_id, cache_dir=f"{cache_dir}/{model_id}", local_files_only=True)

        # self.model = torch.quantization.quantize_dynamic(
        #     self.model,
        #     {torch.nn.Linear},
        #     dtype=torch.qint8
        # )
        # self.model = torch.jit.trace(
        #     self.model, (torch.randn(1, self.model.config.numDims), self.tokenizer)
        # )
        # self.model = torch.jit.freeze(self.model)


    def dim(self) -> int:
        return self.model.config.numDims

    def texts(self, texts):
        with torch.no_grad():
            return self.model.forward(texts, self.tokenizer).tolist()


if __name__ == "__main__":
    texts = [
        'Three blind horses listening to Mozart.',
        'Älgen är skogens konung!',
        'Wie leben Eisbären in der Antarktis?',
        'Вы знали, что все белые медведи левши?'
    ]
    
    model_id = 'sentence-transformers/all-MiniLM-L6-v2'
    embedder = SentenceTransformerEmbedder(model_id)
    print(f"Embedding dimension of {model_id}: {embedder.dim()}")
    import time
    import torch

    torch.set_num_threads(4)

    for _ in range(10):
        start = time.time()
        embeddings = embedder(texts)
        print(f"Generated embeddings in {time.time()-start} seconds.")

    exit()

    

    torch.jit.enable_onednn_fusion(True)

    model_id = 'M-CLIP/LABSE-Vit-L-14'    
    embedder = ClipEmbedder(model_id)
    print(f"Embedding dimension of {model_id}: {embedder.dim()}")

    torch.set_num_threads(4)

    for _ in range(10):
        start = time.time()
        embeddings = embedder.texts(texts)
        print(f"Generated embeddings in {time.time()-start} seconds.")
    