import re
from pathlib import Path
from typing import Annotated

import psycopg2
import typer
from jinja2 import Template

from config import config

app = typer.Typer(help="RisingWave commands.")


class MigrationError(Exception):
    """Error during migration execution."""

    pass


def get_context():
    return {
        "db_host": config.risingwave.rw_cdc_host or config.postgres.db_host,
        "db_port": config.postgres.db_port,
        "db_user": config.risingwave.rw_cdc_user,
        "db_pass": config.risingwave.rw_cdc_pass.get_secret_value(),
        "db_name": config.postgres.db_name,
        "bootstrap_server": config.risingwave.rw_kafka_bootstrap_servers,
        "k_latest_account_favourites_embeddings": config.embed.k_latest_account_favourites_embeddings,
        "k_latest_account_reblogs_embeddings": config.embed.k_latest_account_reblogs_embeddings,
        "k_latest_account_replies_embeddings": config.embed.k_latest_account_replies_embeddings,
        "redis_url": config.redis.url,
    }


def parse_migration(sql):
    up_match = re.search(r"--\s*:up(.*?)(--\s*:down|$)", sql, re.DOTALL)
    down_match = re.search(r"--\s*:down(.*)", sql, re.DOTALL)

    if not up_match:
        raise MigrationError("Migration missing '-- :up' section")

    context = get_context()

    up_sql = Template(up_match.group(1).strip()).render(context)
    down_sql = Template(down_match.group(1).strip()).render(context) if down_match else None

    return up_sql, down_sql


def get_version(migration_dir: Path, file: Path) -> str:
    """Get version string as folder/filename (e.g., 00_base/001_create_pg_source)."""
    return f"{migration_dir.name}/{file.stem}"


def ensure_migration_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP
        );
        ALTER TABLE _migrations SET parallelism = 1;
        """)
        conn.commit()


def get_applied_migrations(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM _migrations;")
        return {row[0] for row in cur.fetchall()}


def get_connection():
    try:
        return psycopg2.connect(
            dbname=config.risingwave.rw_name,
            user=config.risingwave.rw_user,
            password=config.risingwave.rw_pass.get_secret_value(),
            host=config.risingwave.rw_host,
            port=config.risingwave.rw_port,
        )
    except psycopg2.OperationalError as e:
        typer.secho(f"Failed to connect to RisingWave: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


def execute_sql(conn, sql: str, dry_run: bool = False):
    """Execute SQL statements, handling empty queries."""
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    if dry_run:
        for stmt in statements:
            typer.secho(f"  {stmt[:80]}...", fg=typer.colors.YELLOW)
        return

    with conn.cursor() as cur:
        for query in statements:
            try:
                cur.execute(query + ";")
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                raise MigrationError(f"SQL error: {e}\nQuery: {query[:200]}...")


def record_migration(conn, version: str):
    """Record a migration as applied with timestamp."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO _migrations (version, applied_at) VALUES (%s, NOW());",
            (version,),
        )
        conn.commit()


def remove_migration(conn, version: str):
    """Remove a migration record."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM _migrations WHERE version = %s;", (version,))
        conn.commit()


def find_migration_file(version: str) -> tuple[Path, Path] | None:
    """Find migration file by version string. Returns (migration_dir, file) or None."""
    for path in config.risingwave.rw_migrations_paths:
        migration_dir = Path(path)
        for file in migration_dir.glob("*.sql"):
            if get_version(migration_dir, file) == version:
                return migration_dir, file
    return None


@app.command("migrate")
def migrate(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview migrations without applying")
    ] = False,
):
    """Apply pending migrations."""
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    applied_count = 0

    if dry_run:
        typer.secho("Dry run mode - no changes will be made\n", fg=typer.colors.YELLOW)

    for path in config.risingwave.rw_migrations_paths:
        migration_dir = Path(path)

        if not migration_dir.exists():
            typer.secho(f"Warning: {migration_dir} does not exist", fg=typer.colors.YELLOW)
            continue

        for file in sorted(migration_dir.glob("*.sql")):
            version = get_version(migration_dir, file)

            if version in applied:
                continue

            with open(file, "r") as f:
                sql = f.read()

            try:
                up_sql, _ = parse_migration(sql)
            except MigrationError as e:
                typer.secho(f"Error parsing {version}: {e}", fg=typer.colors.RED)
                raise typer.Exit(1)

            if dry_run:
                typer.echo(f"Would apply: {version}")
            else:
                try:
                    execute_sql(conn, up_sql)
                    record_migration(conn, version)
                    typer.secho(f"Applied: {version}", fg=typer.colors.GREEN)
                except MigrationError as e:
                    typer.secho(f"Failed to apply {version}: {e}", fg=typer.colors.RED)
                    raise typer.Exit(1)

            applied_count += 1

    if applied_count == 0:
        typer.echo("No pending migrations")
    elif dry_run:
        typer.echo(f"\n{applied_count} migration(s) would be applied")
    else:
        typer.secho(f"\n{applied_count} migration(s) applied", fg=typer.colors.GREEN)


@app.command("rollback")
def rollback(
    version: Annotated[str | None, typer.Argument(help="Specific migration to rollback")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview rollback without applying")
    ] = False,
):
    """Rollback migrations. Without version, rolls back all. With version, rolls back only that migration."""
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    rolled_back = 0

    if dry_run:
        typer.secho("Dry run mode - no changes will be made\n", fg=typer.colors.YELLOW)

    for path in reversed(config.risingwave.rw_migrations_paths):
        migration_dir = Path(path)

        if not migration_dir.exists():
            continue

        for file in reversed(sorted(migration_dir.glob("*.sql"))):
            file_version = get_version(migration_dir, file)

            if file_version not in applied:
                continue

            if version is not None and version != file_version:
                continue

            with open(file, "r") as f:
                sql = f.read()

            try:
                _, down_sql = parse_migration(sql)
            except MigrationError as e:
                typer.secho(f"Error parsing {file_version}: {e}", fg=typer.colors.RED)
                raise typer.Exit(1)

            if not down_sql:
                typer.secho(
                    f"Warning: {file_version} has no down migration", fg=typer.colors.YELLOW
                )
                if version is not None:
                    raise typer.Exit(1)
                continue

            if dry_run:
                typer.echo(f"Would rollback: {file_version}")
            else:
                try:
                    execute_sql(conn, down_sql)
                    remove_migration(conn, file_version)
                    typer.secho(f"Rolled back: {file_version}", fg=typer.colors.GREEN)
                except MigrationError as e:
                    typer.secho(f"Failed to rollback {file_version}: {e}", fg=typer.colors.RED)
                    raise typer.Exit(1)

            rolled_back += 1

            if version is not None:
                return

    if rolled_back == 0:
        if version:
            typer.secho(f"Migration {version} not found or not applied", fg=typer.colors.RED)
            raise typer.Exit(1)
        else:
            typer.echo("No migrations to rollback")
    elif dry_run:
        typer.echo(f"\n{rolled_back} migration(s) would be rolled back")


@app.command("update")
def update(
    version: Annotated[str, typer.Argument(help="Migration version to update")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview update without applying")
    ] = False,
):
    """Re-apply a specific migration (rollback + migrate)."""
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    if dry_run:
        typer.secho("Dry run mode - no changes will be made\n", fg=typer.colors.YELLOW)

    result = find_migration_file(version)
    if not result:
        typer.secho(f"Migration {version} not found", fg=typer.colors.RED)
        raise typer.Exit(1)

    migration_dir, file = result

    with open(file, "r") as f:
        sql = f.read()

    try:
        up_sql, down_sql = parse_migration(sql)
    except MigrationError as e:
        typer.secho(f"Error parsing {version}: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if version in applied:
        if not down_sql:
            typer.secho(f"Cannot update {version}: no down migration", fg=typer.colors.RED)
            raise typer.Exit(1)

        if dry_run:
            typer.echo(f"Would rollback: {version}")
        else:
            try:
                execute_sql(conn, down_sql)
                remove_migration(conn, version)
                typer.secho(f"Rolled back: {version}", fg=typer.colors.GREEN)
            except MigrationError as e:
                typer.secho(f"Failed to rollback {version}: {e}", fg=typer.colors.RED)
                raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Would apply: {version}")
    else:
        try:
            execute_sql(conn, up_sql)
            record_migration(conn, version)
            typer.secho(f"Applied: {version}", fg=typer.colors.GREEN)
        except MigrationError as e:
            typer.secho(f"Failed to apply {version}: {e}", fg=typer.colors.RED)
            raise typer.Exit(1)


@app.command("status")
def status():
    """Show migration status for all modules."""
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    total_applied = 0
    total_pending = 0

    for path in config.risingwave.rw_migrations_paths:
        migration_dir = Path(path)

        if not migration_dir.exists():
            typer.secho(f"\n{migration_dir.name}: (not found)", fg=typer.colors.YELLOW)
            continue

        files = sorted(migration_dir.glob("*.sql"))
        if not files:
            continue

        typer.echo(f"\n{migration_dir.name}:")

        for file in files:
            version = get_version(migration_dir, file)
            if version in applied:
                typer.secho(f"  [✓] {file.stem}", fg=typer.colors.GREEN)
                total_applied += 1
            else:
                typer.secho(f"  [ ] {file.stem}", fg=typer.colors.WHITE)
                total_pending += 1

    typer.echo(f"\nTotal: {total_applied} applied, {total_pending} pending")


ALTER_KEYWORDS = {
    "index": "INDEX",
    "materialized view": "MATERIALIZED VIEW",
    "table": "TABLE",
    "source": "SOURCE",
    "sink": "SINK",
}


@app.command("set-parallelism")
def set_parallelism(
    n: Annotated[int, typer.Argument(help="Target parallelism for all streaming objects")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview changes without applying")
    ] = False,
):
    """Set streaming parallelism for all streaming objects."""
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT name, relation_type FROM rw_streaming_parallelism WHERE parallelism != %s;",
            (str(n),),
        )
        mismatched = cur.fetchall()

    if not mismatched:
        typer.echo(f"All streaming objects already at parallelism {n}")
        return

    if dry_run:
        typer.secho("Dry run mode - no changes will be made\n", fg=typer.colors.YELLOW)

    updated = 0
    for name, relation_type in mismatched:
        keyword = ALTER_KEYWORDS.get(relation_type)
        if not keyword:
            typer.secho(f"Skipped: {name} (unknown type: {relation_type})", fg=typer.colors.YELLOW)
            continue

        if dry_run:
            typer.echo(f"Would set: {name} ({relation_type}) -> {n}")
        else:
            try:
                with conn.cursor() as cur:
                    cur.execute(f'ALTER {keyword} "{name}" SET PARALLELISM = {n};')
                    conn.commit()
                typer.secho(f"Set: {name} ({relation_type}) -> {n}", fg=typer.colors.GREEN)
            except psycopg2.Error as e:
                conn.rollback()
                typer.secho(f"Failed: {name} ({relation_type}): {e}", fg=typer.colors.RED)
                continue
        updated += 1

    if dry_run:
        typer.echo(f"\n{updated} object(s) would be updated")
    else:
        typer.secho(f"\n{updated} object(s) updated", fg=typer.colors.GREEN)
