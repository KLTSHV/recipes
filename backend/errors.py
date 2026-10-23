"""Единый формат ожидаемых ошибок API."""


class APIError(Exception):
    def __init__(self, status: int, error: str, details: list[str]):
        super().__init__(error)
        self.status = status
        self.error = error
        self.details = details

    def as_dict(self) -> dict:
        return {"error": self.error, "details": self.details}


def not_found() -> APIError:
    return APIError(404, "Not found", ["Рецепт с таким идентификатором не найден"])
