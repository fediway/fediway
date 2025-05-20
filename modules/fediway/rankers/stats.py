import numpy as np

from .base import Ranker


class SimpleStatsRanker(Ranker):
    """
    A simple linear regression ranking model based on status stats and age.
    """

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
        decay: float = 0.5,
    ):
        self.alpha = np.array([coef_fav, coef_reb, coef_rep])
        self.decay = decay

    def predict(self, stats: np.ndarray):
        return (stats[:, :3] * self.alpha.T).sum(axis=1) * np.exp(
            -self.decay * stats[:, 3] / 86400
        )
