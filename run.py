"""Запускает два HTTP-сервера: клиент и REST API, каждый на своём порту."""

import argparse
import os
import threading

from backend.config import Settings
from backend.database import Database
from backend.seed import seed_database
from backend.server import create_server
from frontend.serve import create_frontend_server


def main():
    parser = argparse.ArgumentParser(description="Книга рецептов — запуск клиента и сервера")
    parser.add_argument("--demo", action="store_true", help="Добавить примеры, только если база пуста")
    args = parser.parse_args()
    settings = Settings.from_env()
    client_host = os.getenv("CLIENT_HOST", "127.0.0.1")
    client_port = int(os.getenv("CLIENT_PORT", "5173"))
    api_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
    api_url = os.getenv("API_BASE_URL", f"http://{api_host}:{settings.port}")
    if args.demo:
        seeded = seed_database(Database(settings.database_path))
        print("Добавлены демонстрационные рецепты" if seeded else "Существующие рецепты сохранены")
    # Контекстные менеджеры закрывают первый сокет, если второй порт занят.
    with create_server(settings) as api, create_frontend_server(client_host, client_port, api_url) as client:
        thread = threading.Thread(target=api.serve_forever, daemon=True)
        thread.start()
        print(f"Клиент: http://{client_host}:{client.server_port}", flush=True)
        print(f"API: {api_url}/api/recipes", flush=True)
        print("Остановка: Ctrl+C", flush=True)
        try:
            client.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            api.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
