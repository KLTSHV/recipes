

import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import Settings
from backend.database import Database
from backend.repository import RecipeRepository
from backend.seed import seed_database
from backend.server import create_server


def recipe(**changes):
    return {
        "title": "Овощной суп", "ingredients": "Морковь — 1 шт.\nВода — 1 л",
        "instructions": "Нарежьте овощи и варите 20 минут.", "prep_time": 25,
        "servings": 2, "category": "Супы", "is_favorite": False, **changes,
    }


class APITest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "recipes.db"
        self.settings = Settings(self.db_path, port=0)
        self.start_server()

    def start_server(self):
        self.server = create_server(self.settings)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True
        )
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def tearDown(self):
        self.stop_server()
        self.directory.cleanup()

    def request(self, method, path="/api/recipes", data=None, *, raw=None, headers=None):
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            content = response.read()
            return response.status, (json.loads(content) if content else None), dict(response.getheaders())
        finally:
            connection.close()

    def create(self, **changes):
        status, body, _ = self.request("POST", data=recipe(**changes))
        self.assertEqual(status, 201)
        return body

    def assertBadRequest(self, data=None, *, raw=None):
        status, body, _ = self.request("POST", data=data, raw=raw)
        self.assertEqual(status, 400)
        self.assertIsInstance(body["error"], str)
        self.assertTrue(body["details"])
        # Следующий запрос подтверждает, что сервер продолжает работу.
        self.assertEqual(self.request("GET")[0], 200)

    def test_empty_list(self):
        self.assertEqual(self.request("GET")[:2], (200, []))

    def test_create_and_single_get(self):
        status, created, headers = self.request("POST", data=recipe())
        self.assertEqual(status, 201)
        self.assertIsInstance(created["id"], int)
        self.assertEqual(headers["Location"], f"/api/recipes/{created['id']}")
        self.assertEqual(self.request("GET", headers["Location"])[:2], (200, created))
        self.assertIs(type(created["is_favorite"]), bool)

    def test_list_returns_all_fields(self):
        created = self.create()
        self.assertEqual(self.request("GET")[1], [created])
        self.assertEqual(set(created), set(recipe()) | {"id"})

    def test_optional_defaults(self):
        payload = recipe()
        del payload["category"]
        del payload["is_favorite"]
        status, body, _ = self.request("POST", data=payload)
        self.assertEqual(status, 201)
        self.assertEqual(body["category"], "")
        self.assertIs(body["is_favorite"], False)

    def test_put_replaces_and_resets_optional_fields(self):
        created = self.create(is_favorite=True)
        payload = recipe(title="Новый суп", prep_time=40)
        del payload["category"]
        del payload["is_favorite"]
        status, updated, _ = self.request("PUT", f"/api/recipes/{created['id']}", payload)
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Новый суп")
        self.assertEqual(updated["prep_time"], 40)
        self.assertEqual(updated["category"], "")
        self.assertIs(updated["is_favorite"], False)
        self.assertEqual(updated["id"], created["id"])

    def test_put_requires_all_required_fields(self):
        created = self.create()
        status, _, _ = self.request("PUT", f"/api/recipes/{created['id']}", {"title": "Суп"})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("GET", f"/api/recipes/{created['id']}")[1], created)

    def test_patch_changes_only_supplied_field(self):
        created = self.create()
        status, updated, _ = self.request("PATCH", f"/api/recipes/{created['id']}", {"is_favorite": True})
        self.assertEqual(status, 200)
        self.assertEqual(updated, {**created, "is_favorite": True})

    def test_patch_empty_rejected(self):
        created = self.create()
        self.assertEqual(self.request("PATCH", f"/api/recipes/{created['id']}", {})[0], 400)

    def test_delete_no_content(self):
        created = self.create()
        status, body, headers = self.request("DELETE", f"/api/recipes/{created['id']}")
        self.assertEqual((status, body), (204, None))
        self.assertEqual(headers["Content-Length"], "0")
        self.assertEqual(self.request("GET")[1], [])

    def test_missing_resources_404(self):
        for method in ("GET", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                status, body, _ = self.request(method, "/api/recipes/999", recipe())
                self.assertEqual(status, 404)
                self.assertEqual(body["error"], "Not found")

    def test_ids_not_reused_even_after_restart(self):
        first = self.create()
        self.request("DELETE", f"/api/recipes/{first['id']}")
        self.stop_server()
        self.start_server()
        second = self.create()
        self.assertGreater(second["id"], first["id"])

    def test_persistence_after_restart(self):
        created = self.create(is_favorite=True)
        self.stop_server()
        self.start_server()
        self.assertEqual(self.request("GET")[1], [created])

    def test_invalid_json(self):
        for raw in (b'{"title":', b"not-json", b"", b"\xff", b'{"title":"A","title":"B"}', b'{"prep_time":NaN}'):
            with self.subTest(raw=raw):
                self.assertBadRequest(raw=raw)

    def test_non_object_json(self):
        for raw in (b"[]", b"null", b"123", b'"text"', b"true"):
            with self.subTest(raw=raw):
                self.assertBadRequest(raw=raw)

    def test_missing_required_fields(self):
        for field in ("title", "ingredients", "instructions", "prep_time", "servings"):
            with self.subTest(field=field):
                payload = recipe()
                del payload[field]
                self.assertBadRequest(payload)

    def test_string_limits_and_whitespace(self):
        for field, values in {
            "title": ["", " \n\t", "a" * 201, 123, None],
            "ingredients": ["", "a" * 4001], "instructions": ["", "a" * 10001],
            "category": ["a" * 51, None],
        }.items():
            for value in values:
                with self.subTest(field=field, length=len(value) if isinstance(value, str) else None):
                    self.assertBadRequest(recipe(**{field: value}))

    def test_integer_ranges_and_strict_types(self):
        for field, values in {
            "prep_time": [0, 1441, -1, 2.5, True, "20", None],
            "servings": [0, 51, 2.0, False, "2", None],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertBadRequest(recipe(**{field: value}))

    def test_valid_boundary_values(self):
        self.create(title="a" * 200, ingredients="a" * 4000, instructions="a" * 10000, category="a" * 50, prep_time=1440, servings=50)
        self.create(prep_time=1, servings=1)

    def test_boolean_strict(self):
        for value in (0, 1, "true", "false", None, []):
            with self.subTest(value=value):
                self.assertBadRequest(recipe(is_favorite=value))

    def test_unknown_and_readonly_fields(self):
        self.assertBadRequest(recipe(id=5))
        self.assertBadRequest(recipe(extra="value"))

    def test_invalid_unicode_and_null_character(self):
        self.assertBadRequest(recipe(title="\ud800"))
        self.assertBadRequest(recipe(title="a\x00b"))
        self.assertBadRequest(raw=br'{"\ud800":0}')

    def test_invalid_ids(self):
        for value in ("0", "-1", "abc", "1.5", "9223372036854775808"):
            self.assertEqual(self.request("GET", f"/api/recipes/{value}")[0], 400)

    def test_wrong_content_type(self):
        self.assertEqual(self.request("POST", data=recipe(), headers={"Content-Type": "text/plain"})[0], 400)

    def test_oversized_body(self):
        self.assertBadRequest(raw=json.dumps({"title": "a" * (129 * 1024)}).encode())

    def test_cors_preflight_and_actual_response(self):
        origin = "http://localhost:5173"
        status, body, headers = self.request("OPTIONS", headers={"Origin": origin, "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "content-type"})
        self.assertEqual((status, body), (204, None))
        self.assertEqual(headers["Access-Control-Allow-Origin"], origin)
        self.assertIn("PATCH", headers["Access-Control-Allow-Methods"])
        self.assertEqual(self.request("POST", data=recipe(), headers={"Origin": origin})[2]["Access-Control-Allow-Origin"], origin)
        self.assertNotIn("Access-Control-Allow-Origin", self.request("GET", headers={"Origin": "https://example.org"})[2])

    def test_database_failure_returns_json_500(self):
        with patch.object(RecipeRepository, "list_all", side_effect=sqlite3.OperationalError("test error")):
            with self.assertLogs("backend.server", level="ERROR"):
                status, body, _ = self.request("GET")
        self.assertEqual(status, 500)
        self.assertEqual(body["error"], "Internal server error")
        self.assertNotIn("test error", json.dumps(body))
        self.assertEqual(self.request("GET")[0], 200)

    def test_migrations_idempotent(self):
        self.create()
        Database(self.db_path).migrate()
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)
        self.assertEqual(len(self.request("GET")[1]), 1)

    def test_seed_does_not_overwrite_existing_data(self):
        created = self.create()
        self.assertFalse(seed_database(Database(self.db_path)))
        self.assertEqual(self.request("GET")[1], [created])

    def test_demo_seed_is_idempotent(self):
        database = Database(self.db_path)
        self.assertTrue(seed_database(database))
        first = self.request("GET")[1]
        self.assertEqual(len(first), 6)
        self.assertFalse(seed_database(database))
        self.assertEqual(self.request("GET")[1], first)

    def test_sql_and_html_strings_are_plain_data(self):
        created = self.create(title="Robert'); DROP TABLE recipes; --", ingredients="<script>alert(1)</script>")
        self.assertEqual(self.request("GET")[1], [created])

    def test_unknown_path_and_method(self):
        self.assertEqual(self.request("GET", "/api/unknown")[0], 404)
        status, body, headers = self.request("DELETE")
        self.assertEqual(status, 405)
        self.assertIn("POST", headers["Allow"])
        self.assertTrue(body["details"])


if __name__ == "__main__":
    unittest.main()
