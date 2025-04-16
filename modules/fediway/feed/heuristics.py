
import numpy as np

class Heuristic():
    features: list[str] = []

    def update_seen(self, candidate) -> None:
        pass

    def to_dict(self):
        return {}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def __call__(self, candidates, scores: np.ndarray, features: np.ndarray | None = None) -> np.ndarray:
        raise NotImplemented