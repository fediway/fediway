
from datetime import timedelta
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

from modules.fediway.sources import Source
from modules.fediway.heuristics import Heuristic

class FediwayConfig(BaseConfig):    
    feed_max_age_in_days: int       = 3
    feed_max_sourced_candidates: int  = 500
    feed_max_heavy_candidates: int  = 100
    feed_batch_size: int            = 20
    feed_decay_rate: float          = 1.0

    schwarm_max_status_age_in_days: int = 7

    memgraph_host: str       = 'localhost'
    memgraph_port: int       = 7687
    memgraph_user: str       = ''
    memgraph_pass: SecretStr = ''
    memgraph_name: str       = 'fediway_development'

    arango_host: str = 'localhost'
    arango_port: int = 8529
    arango_name: str = 'herde'
    arango_user: str = 'root'
    arango_pass: str = 'openSesame'
    arango_graph: str = 'herde_graph'

    schwarm_migrations_path: str = 'migrations/schwarm'
    datasets_path: str = 'data/datasets'
    datasets_s3_endpoint: str | None = None

    @property
    def memgraph_url(self):
        return f"bolt://{self.memgraph_host}:{self.memgraph_port}"

    @property
    def memgraph_auth(self) -> tuple[str, str]:
        return (self.memgraph_user, self.memgraph_pass.get_secret_value())

    @property
    def arango_hosts(self) -> str:
        return f"http://{self.arango_host}:{self.arango_port}"

    @property
    def feed_heuristics(self) -> list[Heuristic]:
        from modules.fediway.heuristics import DiversifyHeuristic

        return [
            DiversifyHeuristic(by='status:account_id', penalty=0.1)
        ]

    @property
    def schwarm_max_status_age(self) -> timedelta:
        return timedelta(days=self.schwarm_max_status_age_in_days)

    def max_candidates_per_source(self, n_sources: int):
        return self.feed_max_sourced_candidates // n_sources