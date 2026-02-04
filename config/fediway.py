from datetime import datetime, timedelta

from modules.fediway.heuristics import Heuristic

from .base import BaseConfig
from .sources import SourcesConfig


class FediwayConfig(BaseConfig):
    # module flags - controls both migrations and runtime sources
    collaborative_filtering_enabled: bool = False
    orbit_enabled: bool = False
    features_online_enabled: bool = False
    features_offline_enabled: bool = False

    # feed
    feed_max_age_in_days: int = 3
    feed_max_sourced_candidates: int = 500
    feed_max_heavy_candidates: int = 100
    feed_batch_size: int = 20
    feed_decay_rate: float = 1.0
    feed_session_ttl: int = 3600

    # sources configuration
    sources: SourcesConfig = SourcesConfig()

    # legacy source params (for backward compatibility)
    follows_source_recently_engaged_age_in_days: int = 7

    # datasets
    datasets_path: str = "data/datasets"
    datasets_s3_endpoint: str | None = None

    def feed_max_age(self):
        return datetime.now() - timedelta(days=self.feed_max_age_in_days)

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from modules.fediway.heuristics import DiversifyHeuristic

        return [DiversifyHeuristic(by="status:account_id", penalty=0.1)]

    def max_candidates_per_source(self, n_sources: int):
        return self.feed_max_sourced_candidates // n_sources

    def is_source_enabled(self, source_name: str) -> bool:
        cfg = self.sources.get_source_config(source_name)
        return cfg.enabled if cfg else False

    def get_source_param(self, source_name: str, param: str, default=None):
        cfg = self.sources.get_source_config(source_name)
        if cfg:
            return cfg.params.get(param, default)
        return default
