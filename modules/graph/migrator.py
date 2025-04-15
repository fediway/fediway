
from pathlib import Path

class Migrator:
    def __init__(self, migrations_path: str):
        self.migrations_path = migrations_path

    def get_migrations(self):
        return sorted(Path(self.migrations_path).glob("*.cypher"))