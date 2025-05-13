
import numpy as np

class Heuristic():
    features: list[str] = []

    def update_seen(self, candidate) -> None:
        pass

    def get_state(self):
        return None

    def set_state(self, data):
        pass

    def __call__(self, candidates, scores: np.ndarray, features: np.ndarray | None = None) -> np.ndarray:
        raise NotImplemented