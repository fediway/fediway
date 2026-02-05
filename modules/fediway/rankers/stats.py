import numpy as np
import pandas as pd

from .base import Ranker


class SimpleStatsRanker(Ranker):
    """Linear regression ranking based on engagement stats and time decay."""

    _id = "simple_stats_ranker"
    _tracked_params = ["coef_fav", "coef_reb", "coef_rep", "decay_rate"]

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
        self.coef_fav = coef_fav
        self.coef_reb = coef_reb
        self.coef_rep = coef_rep
        self.decay_rate = decay_rate
        self._alpha = np.array([coef_fav, coef_reb, coef_rep])

    def predict(self, stats: pd.DataFrame):
        return (stats.values[:, :3] * self._alpha.T).sum(axis=1) * np.exp(
            -self.decay_rate * stats.values[:, 3] / 86400
        )
