
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
        'replies_count'
    ]

    def __init__(self, 
                 coef_fav: float = 0.5, 
                 coef_reb: float = 2.0, 
                 coef_rep: float = 2.0):
        self.alpha = np.array([coef_fav, coef_reb, coef_rep])

    def predict(self, stats: np.ndarray):
        return (stats * self.alpha.T).sum(axis=1)