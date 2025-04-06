
import numpy as np

from ..feed import Candidate

class Heuristic():
    def update(self, candidate: Candidate):
        raise NotImplemented

    def __call__(self, scores, meta, seen):
        raise NotImplemented

class DiversifyAccountsHeuristic():
    def __init__(self, 
                 penalty: float = 0.5):
        self.penalty = penalty
        self.account_ids = set()

    def update(self, candidate: Candidate):
        self.account_ids.add(candidate.account_id)

    def __call__(self, 
                 candidates: list[float],
                 scores: np.ndarray):

        mask = np.array([
            (candidate.account_id in self.account_ids) for candidate in candidates
        ], dtype=bool)

        scores[mask] *= self.penalty
        
        return scores