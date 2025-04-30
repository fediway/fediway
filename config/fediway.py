
from datetime import timedelta
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

from modules.fediway.sources import Source
from modules.fediway.feed import Heuristic

class FediwayConfig(BaseConfig):    
    feed_max_age_in_days: int       = 3
    feed_max_light_candidates: int  = 500
    feed_max_heavy_candidates: int  = 100
    feed_batch_size: int            = 20

    herde_max_status_age_in_days: int = 7

    memgraph_host: str       = 'localhost'
    memgraph_port: int       = 7687
    memgraph_user: str       = ''
    memgraph_pass: SecretStr = ''
    memgraph_name: str       = 'fediway_development'

    herde_migrations_path: str = 'migrations/herde'

    @property
    def graph_url(self):
        return f"bolt://{self.memgraph_host}:{self.memgraph_port}"

    @property
    def graph_auth(self) -> tuple[str, str]:
        return (self.memgraph_user, self.memgraph_pass.get_secret_value())

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from app.modules.heuristics import DiversifyAccountsHeuristic

        return [
            DiversifyAccountsHeuristic(penalty=0.1)
        ]

    @property
    def herde_max_status_age(self) -> timedelta:
        return timedelta(days=self.herde_max_status_age_in_days)