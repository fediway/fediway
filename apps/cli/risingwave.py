import re
from pathlib import Path

import psycopg2
import typer
from jinja2 import Template

from config import config

app = typer.Typer(help="RisingWave commands.")


def get_context():
    return {
        "db_host": config.db.rw_pg_host or db_host,
        "db_port": config.db.db_port,
        "db_user": config.db.rw_pg_user,
        "db_pass": config.db.rw_pg_pass.get_secret_value(),
        "db_name": config.db.db_name,
        "bootstrap_server": config.db.rw_kafka_bootstrap_servers,
        "k_latest_account_favourites_embeddings": config.embed.k_latest_account_favourites_embeddings,
        "k_latest_account_reblogs_embeddings": config.embed.k_latest_account_reblogs_embeddings,
        "k_latest_account_replies_embeddings": config.embed.k_latest_account_replies_embeddings,
    }


def env_substitute(sql: str, context: dict):
    return re.sub(
        r"\$\{(\w+)\}", lambda m: str(context.get(m.group(1), m.group(0))), sql
    )


def parse_migration(sql):
    up_sql = re.search(r"--\s*:up(.*?)(--\s*:down|$)", sql, re.DOTALL)
    down_sql = re.search(r"--\s*:down(.*)", sql, re.DOTALL)

    up_sql = Template(up_sql.group(1).strip()).render()
    down_sql = Template(down_sql.group(1).strip()).render() if down_sql else None

    return up_sql, down_sql


def ensure_migration_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP
        );
        """)
        conn.commit()


def get_applied_migrations(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM _migrations;")
        return {row[0] for row in cur.fetchall()}


def get_connection():
    return psycopg2.connect(
        dbname=config.db.rw_name,
        user=config.db.rw_user,
        password=config.db.rw_pass.get_secret_value(),
        host=config.db.rw_host,
        port=config.db.rw_port,
    )


@app.command("migrate")
def migrate():
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    context = get_context()

    for path in config.db.rw_migrations_paths:
        migration_dir = Path(path)

        for file in sorted(migration_dir.glob("*.sql")):
            version = file.stem

            if version in applied:
                continue

            with open(file, "r") as f:
                sql = env_substitute(f.read(), context)

            up_sql, _ = parse_migration(sql)

            with conn.cursor() as cur:
                for query in up_sql.split(";"):
                    try:
                        cur.execute(query + ";")
                        conn.commit()
                    except Exception as e:
                        if str(e) == "can't execute an empty query":
                            continue
                        print(query)
                        raise e
                cur.execute(
                    "INSERT INTO _migrations (version) VALUES (%s);", (version,)
                )
                conn.commit()

            typer.echo(f"Applied migration {version}")


@app.command("rollback")
def rollback(version: str | None = None):
    conn = get_connection()
    ensure_migration_table(conn)
    applied = get_applied_migrations(conn)

    context = get_context()

    for path in reversed(config.db.rw_migrations_paths):
        migration_dir = Path(path)

        for file in reversed(sorted(migration_dir.glob("*.sql"))):
            if version is not None and version != file.stem:
                continue

            with open(file, "r") as f:
                sql = env_substitute(f.read(), context)

            _, down_sql = parse_migration(sql)

            with conn.cursor() as cur:
                print(down_sql)
                cur.execute(down_sql)
                cur.execute("DELETE FROM _migrations WHERE version = %s;", (file.stem,))
                conn.commit()

            typer.echo(f"Rolled back migration {file.stem}")


@app.command("update")
def update(version: str):
    conn = get_connection()
    ensure_migration_table(conn)

    context = get_context()

    for path in reversed(config.db.rw_migrations_paths):
        migration_dir = Path(path)

        for file in reversed(sorted(migration_dir.glob("*.sql"))):
            if version != file.stem:
                continue

            with open(file, "r") as f:
                sql = env_substitute(f.read(), context)

            up_sql, down_sql = parse_migration(sql)

            with conn.cursor() as cur:
                cur.execute(down_sql)
                cur.execute("DELETE FROM _migrations WHERE version = %s;", (version,))
                conn.commit()

                typer.echo(f"Rolled back migration {version}")

            with conn.cursor() as cur:
                for query in up_sql.split(";"):
                    print(query)
                    try:
                        cur.execute(query + ";")
                        conn.commit()
                    except Exception as e:
                        if str(e) == "can't execute an empty query":
                            continue
                        print(query)
                        raise e
                cur.execute(
                    "INSERT INTO _migrations (version) VALUES (%s);", (version,)
                )
                conn.commit()

                typer.echo(f"Applied migration {version}")
