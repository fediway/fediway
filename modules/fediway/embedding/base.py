class Embedder:
    def __init__(self):
        pass

    def __call__(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError


class MultimodalEmbedder:
    def __init__(self):
        pass

    def texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError
