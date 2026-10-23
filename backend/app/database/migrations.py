from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(path: str | Path) -> None:
    """Apply the checked-in Agentropolis SQLite migrations exactly once."""

    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = migration.name
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            if applied:
                continue
            connection.executescript(migration.read_text())
            connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
