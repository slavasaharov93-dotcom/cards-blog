# -*- coding: utf-8 -*-
"""Локальный просмотр собранного сайта.  Запуск: python serve.py [порт]"""
import http.server
import sys
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIST = Path(__file__).resolve().parent / "dist"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def log_message(self, *a):
        pass


# ThreadingHTTPServer — не блокируется на одном соединении.
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
print(f"Сайт открыт: http://127.0.0.1:{PORT}/  (Ctrl+C — остановить)")
httpd.serve_forever()
