"""Almacenamiento de las suscripciones en Vercel: Upstash Redis por su API REST (solo `requests`, sin librerías nuevas).

Vercel no tiene disco permanente, así que lo que en local eran los Excel y los JSON (`data/suscripciones/`, `telegram_chats.json`,
`telegram_sent.json`) vive aquí en tres «hashes» de Redis:

  subs   `alertas|@usuario|<id de la ASADA>` → fila de la suscripción (JSON, con las mismas columnas del Excel)
  chats  `usuario` (sin @, minúsculas)        → Chat ID de Telegram
  sent   clave del envío                      → sello de lo último enviado (para no repetir avisos)

`FakeStore` hace lo mismo en memoria: sirve para las pruebas y para probar sin Redis.
"""
from __future__ import annotations

import os
import threading
from typing import Any

import requests

SUBS, CHATS, SENT = "subs", "chats", "sent"


class StoreError(RuntimeError):
    """No se pudo hablar con el almacenamiento. Nunca incluye la URL ni el token."""


class RedisStore:
    def __init__(self, url: str, token: str, session: Any = requests):
        self.url, self.token, self.session = url.rstrip("/"), token, session

    def _cmd(self, *args: Any) -> Any:
        try:
            response = self.session.post(self.url, json=[str(arg) for arg in args], headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
            body = response.json()
        except (requests.RequestException, ValueError) as error:
            raise StoreError(f"No se pudo hablar con el almacenamiento ({type(error).__name__}).") from None
        if not response.ok or "error" in body:
            raise StoreError(f"El almacenamiento rechazó {args[0]}: {body.get('error', response.status_code)}")
        return body.get("result")

    def hget(self, key: str, field: str) -> str | None:
        return self._cmd("HGET", key, field)

    def hset(self, key: str, field: str, value: str) -> None:
        self._cmd("HSET", key, field, value)

    def hdel(self, key: str, field: str) -> None:
        self._cmd("HDEL", key, field)

    def hgetall(self, key: str) -> dict[str, str]:
        result = self._cmd("HGETALL", key) or []
        if isinstance(result, dict):  # algunas versiones de la API devuelven un objeto
            return {str(field): str(value) for field, value in result.items()}
        return {str(result[i]): str(result[i + 1]) for i in range(0, len(result) - 1, 2)}

    def incr_expire(self, key: str, ttl: int) -> int:
        """Suma 1 al contador; la primera vez le pone `ttl` segundos de vida. Devuelve el valor nuevo."""
        count = int(self._cmd("INCR", key))
        if count == 1:
            self._cmd("EXPIRE", key, ttl)
        return count


class FakeStore:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.counters: dict[str, int] = {}
        self.lock = threading.Lock()

    def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = str(value)

    def hdel(self, key: str, field: str) -> None:
        self.hashes.get(key, {}).pop(field, None)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def incr_expire(self, key: str, ttl: int) -> int:
        with self.lock:
            self.counters[key] = self.counters.get(key, 0) + 1
            return self.counters[key]


def store_from_env(environ: dict[str, str] | None = None, session: Any = requests) -> RedisStore:
    """Lee la conexión que crea la integración de Upstash en Vercel (`KV_REST_API_*` o `UPSTASH_REDIS_REST_*`)."""
    environ = os.environ if environ is None else environ
    url = environ.get("KV_REST_API_URL") or environ.get("UPSTASH_REDIS_REST_URL")
    token = environ.get("KV_REST_API_TOKEN") or environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise StoreError("Falta conectar Upstash Redis al proyecto de Vercel (variables KV_REST_API_URL y KV_REST_API_TOKEN).")
    return RedisStore(url, token, session)
