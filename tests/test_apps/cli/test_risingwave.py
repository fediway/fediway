from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from apps.cli.risingwave import (
    MigrationError,
    get_version,
    parse_migration,
)


# parse_migration tests (12.1)

def test_parse_migration_basic():
    sql = """
    -- :up
    CREATE TABLE foo (id INT);

    -- :down
    DROP TABLE foo;
    """
    up_sql, down_sql = parse_migration(sql)

    assert "CREATE TABLE foo" in up_sql
    assert "DROP TABLE foo" in down_sql


def test_parse_migration_without_down():
    sql = """
    -- :up
    CREATE TABLE foo (id INT);
    """
    up_sql, down_sql = parse_migration(sql)

    assert "CREATE TABLE foo" in up_sql
    assert down_sql is None


def test_parse_migration_missing_up_raises_error():
    sql = """
    CREATE TABLE foo (id INT);
    """
    with pytest.raises(MigrationError, match="missing '-- :up' section"):
        parse_migration(sql)


def test_parse_migration_multiline():
    sql = """
    -- :up
    CREATE TABLE foo (
        id INT,
        name VARCHAR
    );
    CREATE INDEX idx_foo ON foo(id);

    -- :down
    DROP INDEX idx_foo;
    DROP TABLE foo;
    """
    up_sql, down_sql = parse_migration(sql)

    assert "CREATE TABLE foo" in up_sql
    assert "CREATE INDEX idx_foo" in up_sql
    assert "DROP INDEX idx_foo" in down_sql
    assert "DROP TABLE foo" in down_sql


# Jinja templating tests (12.2)

def _mock_context(**overrides):
    context = {
        "db_host": "localhost",
        "db_port": 5432,
        "db_user": "risingwave",
        "db_pass": "secret",
        "db_name": "mastodon",
        "bootstrap_server": "kafka:9092",
        "k_latest_account_favourites_embeddings": 10,
        "k_latest_account_reblogs_embeddings": 10,
        "k_latest_account_replies_embeddings": 10,
        "redis_url": "redis://localhost:6379",
    }
    context.update(overrides)
    return context


def test_parse_migration_renders_jinja_variables():
    sql = """
    -- :up
    CREATE SOURCE pg WITH (
        hostname = '{{ db_host }}',
        port = '{{ db_port }}'
    );
    """
    with patch("apps.cli.risingwave.get_context", return_value=_mock_context()):
        up_sql, _ = parse_migration(sql)

    assert "hostname = 'localhost'" in up_sql
    assert "port = '5432'" in up_sql


def test_parse_migration_renders_multiple_variables():
    sql = """
    -- :up
    CREATE SOURCE pg WITH (
        hostname = '{{ db_host }}',
        username = '{{ db_user }}',
        password = '{{ db_pass }}',
        database.name = '{{ db_name }}'
    );
    """
    with patch("apps.cli.risingwave.get_context", return_value=_mock_context()):
        up_sql, _ = parse_migration(sql)

    assert "hostname = 'localhost'" in up_sql
    assert "username = 'risingwave'" in up_sql
    assert "password = 'secret'" in up_sql
    assert "database.name = 'mastodon'" in up_sql


def test_parse_migration_renders_down_section():
    sql = """
    -- :up
    CREATE SOURCE pg WITH (hostname = '{{ db_host }}');

    -- :down
    DROP SOURCE pg;
    """
    with patch("apps.cli.risingwave.get_context", return_value=_mock_context()):
        _, down_sql = parse_migration(sql)

    assert down_sql == "DROP SOURCE pg;"


def test_parse_migration_renders_kafka_bootstrap():
    sql = """
    -- :up
    CREATE SINK s WITH (
        connector = 'kafka',
        properties.bootstrap.server = '{{ bootstrap_server }}'
    );
    """
    with patch("apps.cli.risingwave.get_context", return_value=_mock_context(bootstrap_server="kafka:29092")):
        up_sql, _ = parse_migration(sql)

    assert "properties.bootstrap.server = 'kafka:29092'" in up_sql


def test_parse_migration_no_variables_unchanged():
    sql = """
    -- :up
    SELECT * FROM users;
    """
    with patch("apps.cli.risingwave.get_context", return_value=_mock_context()):
        up_sql, _ = parse_migration(sql)

    assert "SELECT * FROM users" in up_sql


# get_version tests (12.4)

def test_get_version_includes_folder_and_filename():
    migration_dir = Path("/path/to/migrations/risingwave/00_base")
    file = Path("/path/to/migrations/risingwave/00_base/001_create_pg_source.sql")

    version = get_version(migration_dir, file)

    assert version == "00_base/001_create_pg_source"


def test_get_version_different_folders():
    cases = [
        ("00_base", "001_create_pg_source.sql", "00_base/001_create_pg_source"),
        ("01_feed", "001_create_feed_tables.sql", "01_feed/001_create_feed_tables"),
        ("02_engagement", "003_create_events.sql", "02_engagement/003_create_events"),
        ("06_orbit", "001_create_orbit_views.sql", "06_orbit/001_create_orbit_views"),
    ]

    for folder, filename, expected in cases:
        migration_dir = Path(f"/migrations/risingwave/{folder}")
        file = Path(f"/migrations/risingwave/{folder}/{filename}")

        version = get_version(migration_dir, file)

        assert version == expected


def test_get_version_strips_sql_extension():
    migration_dir = Path("/path/00_base")
    file = Path("/path/00_base/001_test.sql")

    version = get_version(migration_dir, file)

    assert not version.endswith(".sql")
    assert version == "00_base/001_test"
