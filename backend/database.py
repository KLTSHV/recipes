"""Соединения SQLite и последовательные транзакционные SQL-миграции."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            with self.connect() as connection:
                # Блокировка до проверки версии исключает двойную миграцию.
                connection.execute("BEGIN IMMEDIATE")
                if connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (migration.name,)
                ).fetchone():
                    continue
                # Миграции проекта состоят из простых SQL-операторов без триггеров.
                for statement in migration.read_text(encoding="utf-8").split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)", (migration.name,)
                )


if __name__ == "__main__":
    from .config import Settings

    database = Database(Settings.from_env().database_path)
    database.migrate()
    print(f"Миграции применены: {database.path}")
