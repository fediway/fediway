from datetime import datetime, timedelta

from modules.fediway.heuristics import Heuristic

from .base import BaseConfig


class FediwayConfig(BaseConfig):
    # feed
    feed_max_age_in_days: int = 3
    feed_max_sourced_candidates: int = 500
    feed_max_heavy_candidates: int = 100
    feed_batch_size: int = 20
    feed_decay_rate: float = 1.0
    feed_session_ttl: int = 6_000

    # sources
    follows_source_recently_engaged_age_in_days: int = 7

    # datasets
    datasets_path: str = "data/datasets"
    datasets_s3_endpoint: str | None = None

    # kirby (ML ranker)
    kirby_path: str = "models/kirby_v0.1"
    kirby_label_weight_is_favourited: float = 0.5
    kirby_label_weight_is_reblogged: float = 2.0
    kirby_label_weight_is_replied: float = 2.0
    kirby_label_weight_is_reply_engaged_by_author: float = 5.0

    def feed_max_age(self):
        return datetime.now() - timedelta(days=self.feed_max_age_in_days)

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from modules.fediway.heuristics import DiversifyHeuristic

        return [DiversifyHeuristic(by="status:account_id", penalty=0.1)]

    def max_candidates_per_source(self, n_sources: int):
        return self.feed_max_sourced_candidates // n_sources
