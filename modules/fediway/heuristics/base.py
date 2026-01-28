import numpy as np


class Heuristic:
    features: list[str] = []

    def get_params(self):
        return {}

    def name(self):
        return self.__class__.__name__

    def update_seen(self, candidate) -> None:
        pass

    def get_state(self):
        return None

    def set_state(self, data):
        pass

    def __call__(self, candidates, features: np.ndarray | None = None) -> np.ndarray:
        raise NotImplementedError
