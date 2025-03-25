
import numpy as np
from sqlmodel import Session, select

from ..feed import Candidate
from ..models import StatusStats
from .base import Ranker

class LightStatsRanker(Ranker):
    '''
    A simple ranking model base on status stats.
    '''

    def __init__(self, 
                 coef_fav: float = 0.5, 
                 coef_reb: float = 2.0, 
                 coef_rep: float = 2.0):
        self.alpha = np.array([coef_fav, coef_reb, coef_rep])

    def scores(self, candidates: list[Candidate], db: Session):
        candidate_ids = [candidate.status_id for candidate in candidates]

        rows = db.exec(
            select(StatusStats).where(StatusStats.status_id.in_(candidate_ids))
        ).all()

        stats = np.array([
            [row.favourites_count, row.reblogs_count, row.replies_count] for row in rows
        ])

        scores = (stats * self.alpha.T).sum(axis=1)
        scores_map = {row.status_id: score for row, score in zip(rows, scores)}

        return [scores_map[id] for id in candidate_ids]