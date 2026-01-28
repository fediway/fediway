import numpy as np
from redis import Redis

from ..base import Source


class StatusBasedCollaborativeFilteringSource(Source):
    def __init__(
        self,
        r: Redis,
        account_id: int,
    ):
        self.r = r
        self.account_id = account_id

    def name(self):
        return "status_based_collaborative_filtering"

    def redis_key(self):
        return f"rec:status_sim:{self.account_id}"

    def _encode(self, data):
        candidates = data.split("status_ids")[1].split("{")[1].split("}")[0].split(",")
        scores = data.split("scores")[1].split("{")[1].split("}")[0].split(",")
        return candidates, scores

    def collect(self, limit: int):
        if not self.r.exists(self.redis_key()):
            return []

        candidates, scores = self._encode(self.r.get(self.redis_key()))

        idx = np.argsort(scores)[:limit]
        return np.array(candidates)[idx].tolist()
