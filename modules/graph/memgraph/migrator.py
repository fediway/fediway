

from pathlib import Path
from loguru import logger

from ..migrator import Migrator

class MemgraphMigrator(Migrator):
    def __init__(self, driver, *pargs, **kwargs):
        self.driver = driver
        super().__init__(*pargs, **kwargs)

    def _execute_query(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, parameters=params or {})

            # Consume the result immediately for write queries
            if not query.strip().upper().startswith("MATCH"):
                result.consume()
            else:
                # For read queries, return the records
                return list(result)

    def migrate(self):
        # Create migration tracking constraint
        self._execute_query(
            "CREATE CONSTRAINT ON (v:__Migration) ASSERT v.version IS UNIQUE"
        )

        # Get existing migrations
        result = self._execute_query("MATCH (v:__Migration) RETURN v.version AS version")
        applied_versions = {record["version"] for record in result}

        for migration in self.get_migrations():
            version = migration.stem

            if version in applied_versions:
                continue

            logger.info(f"Start migrating '{version}'.")
            
            with open(migration) as f:
                queries = [q.strip() for q in f.read().split(';') if q.strip()]

                for query in queries:
                    self._execute_query(query)

            self._execute_query(
                "CREATE (v:__Migration {version: $version})",
                {"version": version}
            )

            logger.info(f"Finished migrating '{version}'.")