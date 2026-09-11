#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local static server for apps/opt-catalog with order stub."""

from __future__ import annotations

import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ORDERS = DATA / "orders.json"
HOST = "127.0.0.1"
PORT = 8765

_lock = threading.Lock()


def _load_orders() -> list:
    if not ORDERS.exists():
        return []
    try:
        raw = json.loads(ORDERS.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _save_order(payload: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with _lock:
        orders = _load_orders()
        orders.append({"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"), "payload": payload})
        ORDERS.write_text(json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") + "/"
        if path != "/api/opt/order/":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"ok": False, "error": "Некорректный JSON"})
            return
        if not (payload.get("name") or "").strip() or not (payload.get("phone") or "").strip():
            self._json(400, {"ok": False, "error": "Укажите имя и телефон"})
            return
        if not payload.get("items"):
            self._json(400, {"ok": False, "error": "Корзина пуста"})
            return
        _save_order(payload)
        self._json(200, {"ok": True, "local": True})

    def _json(self, code: int, data: dict) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"opt-catalog: http://{HOST}:{PORT}/")
    print(f"orders file: {ORDERS}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstop")


if __name__ == "__main__":
    main()
