"""Pequeñas utilidades para los handlers de `api/` (`BaseHTTPRequestHandler`)."""
from __future__ import annotations

import json


def send_json(handler, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_body(handler, limit: int = 20_000) -> bytes:
    """El cuerpo de la petición, con tope: un formulario de suscripción nunca pesa más de unos cientos de bytes."""
    length = int(handler.headers.get("Content-Length") or 0)
    return handler.rfile.read(min(max(length, 0), limit))


def client_ip(handler) -> str:
    forwarded = handler.headers.get("x-forwarded-for") or ""
    return forwarded.split(",")[0].strip() or handler.headers.get("x-real-ip") or "?"
