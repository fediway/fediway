from feast.infra.offline_stores.contrib.postgres_offline_store.postgres import (
    PostgreSQLOfflineStoreConfig,
    PostgreSQLOfflineStore,
)


class RisingwaveOfflineStoreConfig(PostgreSQLOfflineStoreConfig):
    kafka_bootstrap_servers: str


class RisingwaveOfflineStore(PostgreSQLOfflineStore):
    pass
