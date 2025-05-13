
import numpy as np

from .base import Heuristic

class DiversifyHeuristic(Heuristic):
    features = []

    def __init__(self, 
                 by: str,
                 penalty: float = 0.5,
                 seen_ids = set()):
        self.features = [by]
        self.penalty = penalty
        self.seen_ids = set(seen_ids)

    def get_state(self):
        return {'seen_ids': list(self.seen_ids)}

    def set_state(self, state):
        self.seen_ids = set(state.get('seen_ids', []))

    def update_seen(self, candidate, features):
        self.seen_ids.add(features[0])

    def __call__(self, 
                 candidates: list[float],
                 scores: np.ndarray,
                 features):
        if len(scores) == 0:
            return scores
        
        if len(self.seen_ids) == 0:
            return scores
        
        mask = np.array([
            (seen_ids in self.seen_ids) for seen_ids in features[:, 0]
        ], dtype=bool)

        scores[mask] *= self.penalty
        
        return scores