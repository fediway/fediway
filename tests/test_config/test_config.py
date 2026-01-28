import pytest


def test_config_imports():
    """All config classes should be importable."""
    from config import (
        config,
        ApiConfig,
        AppConfig,
        BaseConfig,
        CorsConfig,
        EmbedConfig,
        FeastConfig,
        FediwayConfig,
        FilesConfig,
        GeoLocationConfig,
        KafkaConfig,
        LoggingConfig,
        PostgresConfig,
        QdrantConfig,
        RedisConfig,
        RisingWaveConfig,
        TasksConfig,
    )


def test_config_class_attributes():
    """Config class should have all expected service configs."""
    from config import config

    assert hasattr(config, "api")
    assert hasattr(config, "app")
    assert hasattr(config, "cors")
    assert hasattr(config, "embed")
    assert hasattr(config, "feast")
    assert hasattr(config, "fediway")
    assert hasattr(config, "files")
    assert hasattr(config, "geo")
    assert hasattr(config, "kafka")
    assert hasattr(config, "logging")
    assert hasattr(config, "postgres")
    assert hasattr(config, "qdrant")
    assert hasattr(config, "redis")
    assert hasattr(config, "risingwave")
    assert hasattr(config, "tasks")


def test_backward_compat_db_alias():
    """config.db should be an alias for config.postgres."""
    from config import config

    assert config.db is config.postgres


def test_postgres_config():
    """PostgresConfig should have expected attributes."""
    from config import PostgresConfig

    pg = PostgresConfig()
    assert hasattr(pg, "db_host")
    assert hasattr(pg, "db_port")
    assert hasattr(pg, "db_user")
    assert hasattr(pg, "db_pass")
    assert hasattr(pg, "db_name")
    assert hasattr(pg, "url")


def test_postgres_url_property():
    """PostgresConfig.url should return a SQLAlchemy URL."""
    from config import PostgresConfig
    from sqlalchemy import URL

    pg = PostgresConfig()
    url = pg.url
    assert isinstance(url, URL)
    assert url.drivername == "postgresql"


def test_risingwave_config():
    """RisingWaveConfig should have expected attributes."""
    from config import RisingWaveConfig

    rw = RisingWaveConfig()
    assert hasattr(rw, "rw_host")
    assert hasattr(rw, "rw_port")
    assert hasattr(rw, "rw_user")
    assert hasattr(rw, "rw_pass")
    assert hasattr(rw, "rw_name")
    assert hasattr(rw, "rw_migrations_paths")
    assert hasattr(rw, "rw_cdc_host")
    assert hasattr(rw, "rw_cdc_user")
    assert hasattr(rw, "rw_cdc_pass")
    assert hasattr(rw, "rw_kafka_bootstrap_servers")
    assert hasattr(rw, "url")


def test_risingwave_url_property():
    """RisingWaveConfig.url should return a SQLAlchemy URL."""
    from config import RisingWaveConfig
    from sqlalchemy import URL

    rw = RisingWaveConfig()
    url = rw.url
    assert isinstance(url, URL)
    assert url.drivername == "postgresql"


def test_files_config():
    """FilesConfig should have expected attributes."""
    from config import FilesConfig

    files = FilesConfig()
    assert hasattr(files, "paperclip_root_url")
    assert hasattr(files, "s3_enabled")
    assert hasattr(files, "s3_alias_host")
    assert hasattr(files, "build_file_url")
    assert hasattr(files, "interpolate_file_path")


def test_tasks_config():
    """TasksConfig should have expected attributes."""
    from config import TasksConfig

    tasks = TasksConfig()
    assert hasattr(tasks, "worker_host")
    assert hasattr(tasks, "worker_port")
    assert hasattr(tasks, "worker_pass")
    assert hasattr(tasks, "worker_url")


def test_tasks_worker_url_property():
    """TasksConfig.worker_url should return a redis URL string."""
    from config import TasksConfig

    tasks = TasksConfig()
    url = tasks.worker_url
    assert isinstance(url, str)
    assert url.startswith("redis://")


def test_config_instances_via_main_config():
    """Accessing configs via main config class should work."""
    from config import config

    assert config.postgres.db_host is not None
    assert config.postgres.db_port == 5432

    assert config.risingwave.rw_host is not None
    assert config.risingwave.rw_port == 4566

    assert config.files.paperclip_root_url is not None

    assert config.tasks.worker_host is not None


def test_risingwave_separate_from_postgres():
    """RisingWave config should be separate from PostgreSQL config."""
    from config import config

    # Different classes
    assert type(config.postgres).__name__ == "PostgresConfig"
    assert type(config.risingwave).__name__ == "RisingWaveConfig"

    # Different default ports
    assert config.postgres.db_port == 5432
    assert config.risingwave.rw_port == 4566
