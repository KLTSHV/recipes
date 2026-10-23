"""HTTP-слой REST API на стандартной библиотеке Python."""

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .config import Settings
from .database import Database
from .errors import APIError
from .repository import RecipeRepository
from .validation import validate_recipe

MAX_BODY_BYTES = 128 * 1024
LOG = logging.getLogger(__name__)


def reject_constant(value: str):
    raise ValueError(f"Invalid JSON constant: {value}")


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def make_handler(repository: RecipeRepository, settings: Settings):
    class RecipeHandler(BaseHTTPRequestHandler):
        server_version = "RecipesAPI/1.0"

        def log_message(self, format, *args):
            LOG.info("%s %s", self.address_string(), format % args)

        def _respond(self, status: int, payload=None, headers=None):
            body = b"" if payload is None else json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Vary", "Origin")
            if payload is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            origin = self.headers.get("Origin")
            if origin in settings.allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Expose-Headers", "Location")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _read_json(self):
            if self.headers.get("Transfer-Encoding"):
                raise APIError(400, "Bad request", ["Используйте Content-Length для тела запроса"])
            content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                raise APIError(400, "Bad request", ["Требуется заголовок Content-Type: application/json"])
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise APIError(400, "Bad request", ["Некорректный Content-Length"]) from None
            if not 1 <= length <= MAX_BODY_BYTES:
                raise APIError(400, "Bad request", ["Тело запроса пустое или превышает 128 КиБ"])
            try:
                return json.loads(
                    self.rfile.read(length).decode("utf-8"),
                    parse_constant=reject_constant,
                    object_pairs_hook=unique_object,
                )
            except (ValueError, UnicodeDecodeError, RecursionError):
                raise APIError(400, "Bad request", ["Некорректный JSON в теле запроса"]) from None

        def _route(self):
            path = urlsplit(self.path).path
            match = re.fullmatch(r"/api/recipes(?:/([^/]+))?/?", path)
            if not match:
                raise APIError(404, "Not found", ["Эндпоинт не найден"])
            raw_id = match.group(1)
            recipe_id = None
            if raw_id is not None:
                if not re.fullmatch(r"[0-9]{1,19}", raw_id) or not 1 <= int(raw_id) <= 9223372036854775807:
                    raise APIError(400, "Validation failed", ["id должен быть положительным целым числом"])
                recipe_id = int(raw_id)
            method = self.command
            if method == "OPTIONS":
                return self._respond(204)
            if method == "GET":
                value = repository.list_all() if recipe_id is None else repository.get(recipe_id)
                return self._respond(200, value)
            if method == "POST" and recipe_id is None:
                value = repository.create(validate_recipe(self._read_json()))
                return self._respond(201, value, {"Location": f"/api/recipes/{value['id']}"})
            if method in ("PUT", "PATCH") and recipe_id is not None:
                # Существование проверяется до валидации тела: отсутствующая запись → 404.
                repository.get(recipe_id)
                data = validate_recipe(self._read_json(), partial=method == "PATCH")
                return self._respond(200, repository.update(recipe_id, data))
            if method == "DELETE" and recipe_id is not None:
                repository.delete(recipe_id)
                return self._respond(204)
            allowed = "GET, POST, OPTIONS" if recipe_id is None else "GET, PUT, PATCH, DELETE, OPTIONS"
            return self._respond(405, {"error": "Method not allowed", "details": ["Метод не поддерживается для этого пути"]}, {"Allow": allowed})

        def _dispatch(self):
            self.connection.settimeout(10)
            try:
                self._route()
            except APIError as error:
                self._respond(error.status, error.as_dict())
            except (BrokenPipeError, ConnectionResetError):
                LOG.info("Клиент закрыл соединение")
            except Exception:
                LOG.exception("Ошибка обработки запроса")
                self._respond(500, {"error": "Internal server error", "details": ["Не удалось выполнить запрос. Попробуйте ещё раз."]})

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _dispatch

    return RecipeHandler


def create_server(settings: Settings) -> ThreadingHTTPServer:
    database = Database(settings.database_path)
    database.migrate()
    repository = RecipeRepository(database)
    server = ThreadingHTTPServer((settings.host, settings.port), make_handler(repository, settings))
    server.daemon_threads = True
    return server


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    with create_server(settings) as server:
        print(f"API: http://{settings.host}:{server.server_port}/api/recipes", flush=True)
        print(f"SQLite: {settings.database_path}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
