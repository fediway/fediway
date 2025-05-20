from urllib.parse import quote
from pydantic import SecretStr

from .base import BaseConfig


class TasksConfig(BaseConfig):
    worker_host: str = "localhost"
    worker_port: int = 6379
    worker_pass: SecretStr = ""

    compute_account_ranks_every_n_seconds: int = 10 * 60
    compute_tag_ranks_every_n_seconds: int = 10 * 60
    clean_memgraph_every_n_seconds: int = 10 * 60

    @property
    def worker_url(self):
        password = quote(self.worker_pass.get_secret_value())
        return f"redis://:{password}@{self.worker_host}:{self.worker_port}/0"
