"""Connection helper and a tiny migration runner (numbered .sql files, applied in order)."""

import sys
from pathlib import Path

import psycopg

from tripwire.config import load_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def connect(url: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(url or load_settings().database_url)
    conn.execute(
        "SET TIME ZONE 'UTC'"
    )  # all times are UTC (CLAUDE.md), whatever the server default
    conn.commit()
    return conn


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply every migration not yet recorded. Returns the names applied this run."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        conn.execute(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)
    conn.commit()
    return applied


if __name__ == "__main__":
    if sys.argv[1:] == ["migrate"]:
        with connect() as c:
            print("applied:", migrate(c) or "nothing new")
    else:
        sys.exit("usage: python -m tripwire.db migrate")
