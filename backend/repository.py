"""CRUD-хранилище. Значения передаются в SQL только через параметры."""

from .database import Database
from .errors import not_found
from .models import Recipe
from .validation import ALLOWED_FIELDS

FIELDS = ("title", "ingredients", "instructions", "prep_time", "servings", "category", "is_favorite")


class RecipeRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_all(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM recipes ORDER BY id DESC").fetchall()
            return [Recipe.from_row(row).as_dict() for row in rows]

    def get(self, recipe_id: int) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
            if row is None:
                raise not_found()
            return Recipe.from_row(row).as_dict()

    def create(self, data: dict) -> dict:
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"INSERT INTO recipes ({', '.join(FIELDS)}) VALUES ({', '.join('?' for _ in FIELDS)})",
                tuple(data[field] for field in FIELDS),
            )
            row = connection.execute("SELECT * FROM recipes WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return Recipe.from_row(row).as_dict()

    def update(self, recipe_id: int, data: dict) -> dict:
        if not data or set(data) - ALLOWED_FIELDS:
            raise ValueError("Repository accepts only validated, non-empty data")
        with self.database.connect() as connection:
            assignments = ", ".join(f"{field} = ?" for field in data)
            cursor = connection.execute(
                f"UPDATE recipes SET {assignments} WHERE id = ?", (*data.values(), recipe_id)
            )
            if cursor.rowcount == 0:
                raise not_found()
            row = connection.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
            return Recipe.from_row(row).as_dict()

    def delete(self, recipe_id: int) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
            if cursor.rowcount == 0:
                raise not_found()
