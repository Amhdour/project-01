from __future__ import annotations

from pathlib import Path
import sqlite3


def apply_migrations(conn: sqlite3.Connection) -> None:
    versions_dir = Path(__file__).resolve().parent / "alembic" / "versions"
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}

    for migration in sorted(versions_dir.glob("*.sql")):
        version = migration.stem
        if version in applied:
            continue
        sql_text = migration.read_text()
        conn.executescript(sql_text)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
    conn.commit()
