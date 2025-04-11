
import numpy as np

class Heuristic():
    features: list[str] = []

    def update_seen(self, candidate) -> None:
        pass

    def __call__(self, candidates, scores: np.ndarray, features: np.ndarray | None = None) -> np.ndarray:
        raise NotImplemented