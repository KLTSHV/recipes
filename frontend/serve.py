"""HTTP-сервер клиента. /config.js задаёт адрес API из окружения или аргумента."""

import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

FRONTEND_DIR = Path(__file__).resolve().parent


def create_frontend_server(host="127.0.0.1", port=5173, api_url="http://127.0.0.1:8000"):
    class FrontendHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path == "/config.js":
                config = json.dumps({"API_BASE_URL": api_url.rstrip("/")})
                body = f"window.RECIPES_CONFIG = {config};\n".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    return ThreadingHTTPServer((host, port), partial(FrontendHandler, directory=str(FRONTEND_DIR)))


def main():
    parser = argparse.ArgumentParser(description="Запуск клиента коллекции рецептов")
    parser.add_argument("--host", default=os.getenv("CLIENT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CLIENT_PORT", "5173")))
    parser.add_argument("--api-url", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    with create_frontend_server(args.host, args.port, args.api_url) as server:
        print(f"Клиент: http://{args.host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
