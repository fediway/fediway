
from datetime import timedelta

from .base import BaseConfig

from modules.fediway.sources import Source
from modules.fediway.feed import Heuristic

class FediwayConfig(BaseConfig):    
    feed_max_age_in_days: int       = 3
    feed_max_light_candidates: int  = 1000
    feed_max_heavy_candidates: int  = 100
    feed_batch_size: int            = 10

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from app.modules.heuristics import DiversifyAccountsHeuristic

        return [
            DiversifyAccountsHeuristic(penalty=0.1)
        ]