
from datetime import timedelta
from pydantic import SecretStr
from sqlalchemy import URL

from .base import BaseConfig

from modules.fediway.sources import Source
from modules.fediway.feed import Heuristic

class TasksConfig(BaseConfig):    
    worker_host: str = 'localhost'
    worker_port: int = 6379
    worker_password: str = ''

    compute_account_ranks_every_n_seconds: int = 10 * 60
    compute_tag_ranks_every_n_seconds: int = 10 * 60
    clean_memgraph_every_n_seconds: int = 10 * 60

    @property
    def worker_url(self):
        return f"redis://:{self.worker_password}@{self.worker_host}:{self.worker_port}/0"