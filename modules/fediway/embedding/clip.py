from .base import MultimodalEmbedder


class ClipEmbedder(MultimodalEmbedder):
    def __init__(self, model_id: str, cache_dir: str = "data"):
        from multilingual_clip import pt_multilingual_clip
        import transformers

        self.model = pt_multilingual_clip.MultilingualCLIP.from_pretrained(
            model_id, cache_dir=f"{cache_dir}/{model_id}"
        )
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_id, cache_dir=f"{cache_dir}/{model_id}"
        )

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
        "Three blind horses listening to Mozart.",
        "Älgen är skogens konung!",
        "Wie leben Eisbären in der Antarktis?",
        "Вы знали, что все белые медведи левши?",
    ]

    torch.jit.enable_onednn_fusion(True)

    model_id = "M-CLIP/LABSE-Vit-L-14"
    embedder = ClipEmbedder(model_id)
    print(f"Embedding dimension of {model_id}: {embedder.dim()}")

    torch.set_num_threads(4)

    for _ in range(10):
        start = time.time()
        embeddings = embedder.texts(texts)
        print(f"Generated embeddings in {time.time() - start} seconds.")
