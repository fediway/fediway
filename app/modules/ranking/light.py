
import numpy as np
from sqlmodel import Session, select

from ..feed import Candidate
from ..models import StatusStats
from .base import Ranker

class LightStatsRanker(Ranker):
    '''
    A simple ranking model base on status stats.
    '''

    features = [
        'favourites_count',
        'reblogs_count',
        'replies_count',
        'age_in_seconds',
    ]

    def __init__(self, 
                 coef_fav: float = 0.5, 
                 coef_reb: float = 2.0, 
                 coef_rep: float = 2.0,
                 decay: float = 0.1):
        self.alpha = np.array([coef_fav, coef_reb, coef_rep])
        self.decay = decay

    def predict(self, stats: np.ndarray):
        return (stats[:, :3] * self.alpha.T).sum(axis=1) * np.exp(-self.decay * stats[:, 3] / 86400)