import numpy as np
import pandas as pd

from .base import Ranker


class SimpleStatsRanker(Ranker):
    """
    A simple linear regression ranking model based on status stats and age.
    """
    __name__ = "simple_stats_ranker"

    features = [
        "status:favourites_count",
        "status:reblogs_count",
        "status:replies_count",
        "status:age_in_seconds",
    ]

    def __init__(
        self,
        coef_fav: float = 0.5,
        coef_reb: float = 2.0,
        coef_rep: float = 2.0,
        decay_rate: float = 0.5,
    ):
        self.alpha = np.array([coef_fav, coef_reb, coef_rep])
        self.decay_rate = decay_rate

    def predict(self, stats: pd.DataFrame):
        return (stats.values[:, :3] * self.alpha.T).sum(axis=1) * np.exp(
            -self.decay_rate * stats.values[:, 3] / 86400
        )
