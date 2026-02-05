from datetime import datetime, timedelta

from .base import BaseConfig


class FediwayConfig(BaseConfig):
    # module flags
    collaborative_filtering_enabled: bool = False
    orbit_enabled: bool = False
    features_online_enabled: bool = False
    features_offline_enabled: bool = False

    # feed limits
    feed_max_age_in_days: int = 3
    feed_max_sourced_candidates: int = 500
    feed_max_heavy_candidates: int = 100
    feed_batch_size: int = 20
    feed_decay_rate: float = 1.0
    feed_session_ttl: int = 3600

    # datasets
    datasets_path: str = "data/datasets"
    datasets_s3_endpoint: str | None = None

    def feed_max_age(self):
        return datetime.now() - timedelta(days=self.feed_max_age_in_days)

    def max_candidates_per_source(self, n_sources: int):
        return self.feed_max_sourced_candidates // n_sources
