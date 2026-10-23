"""Модель записи и преобразование SQLite → JSON."""

from dataclasses import asdict, dataclass
from sqlite3 import Row


@dataclass(frozen=True)
class Recipe:
    id: int
    title: str
    ingredients: str
    instructions: str
    prep_time: int
    servings: int
    category: str
    is_favorite: bool

    @classmethod
    def from_row(cls, row: Row) -> "Recipe":
        return cls(**{**dict(row), "is_favorite": bool(row["is_favorite"])})

    def as_dict(self) -> dict:
        return asdict(self)
