
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
    feed_batch_size: int            = 10

    graph_host: str       = 'localhost'
    graph_port: int       = 7687
    graph_user: str       = ''
    graph_pass: SecretStr = ''
    graph_name: str       = 'fediway_development'

    herde_migrations_path: str = 'migrations/herde'

    @property
    def graph_url(self):
        return f"bolt://{self.graph_host}:{self.graph_port}"

    @property
    def graph_auth(self) -> tuple[str, str]:
        return (self.graph_user, self.graph_pass.get_secret_value())

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from app.modules.heuristics import DiversifyAccountsHeuristic

        return [
            DiversifyAccountsHeuristic(penalty=0.1)
        ]

