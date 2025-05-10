
import numpy as np

from .base import Heuristic

class DiversifyAccountsHeuristic(Heuristic):
    features = ['status:account_id']

    def __init__(self, 
                 penalty: float = 0.5,
                 account_ids = set()):
        self.penalty = penalty
        self.account_ids = set(account_ids)

    def to_dict(self):
        return {
            'penalty': self.penalty,
            'account_ids': list(self.account_ids),
        }

    def update_seen(self, candidate, features):
        self.account_ids.add(features[0])

    def __call__(self, 
                 candidates: list[float],
                 scores: np.ndarray,
                 features):
        
        if len(self.account_ids) == 0:
            return scores
        
        mask = np.array([
            (account_id in self.account_ids) for account_id in features[:, 0]
        ], dtype=bool)

        scores[mask] *= self.penalty
        
        return scores