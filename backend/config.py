"""Настройки: переменные окружения имеют приоритет над .env."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip():
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class Settings:
    database_path: Path
    host: str = "127.0.0.1"
    port: int = 8000
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173", "http://localhost:5173"
    )

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        database = Path(os.getenv("DATABASE_PATH", "backend/data/recipes.db"))
        if not database.is_absolute():
            database = PROJECT_ROOT / database
        origins = os.getenv(
            "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
        )
        return cls(
            database_path=database,
            host=os.getenv("API_HOST", "127.0.0.1"),
            port=int(os.getenv("API_PORT", "8000")),
            allowed_origins=tuple(x.strip() for x in origins.split(",") if x.strip()),
        )
