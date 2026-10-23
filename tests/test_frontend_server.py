"""Проверка доставки клиента и настройки API без зависимости от браузера"""

import http.client
import threading
import unittest

from frontend.serve import create_frontend_server


class FrontendServerTest(unittest.TestCase):
    def test_static_files_and_environment_config(self):
        with create_frontend_server(port=0, api_url="http://localhost:9000") as server:
            thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
            thread.start()
            try:
                for path, expected in (
                    ("/", "По вкусу"), ("/styles.css", ".recipe-grid"),
                    ("/js/app.js", "api.replace"), ("/config.js", "http://localhost:9000"),
                ):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                    connection.request("GET", path)
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertIn(expected, response.read().decode("utf-8"))
                    connection.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)
