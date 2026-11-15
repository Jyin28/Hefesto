"""POST /api/suscripciones: el formulario del newsletter de Telegram (Predicciones). Lógica en `servidor/rutas.py`."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar `servidor/` (carpeta hermana de api/)

from servidor import rutas  # noqa: E402
from servidor.respuesta import client_ip, read_body, send_json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        send_json(self, *rutas.suscribir(read_body(self), client_ip(self)))

    def log_message(self, *args):  # sin registro de cada petición: lleva direcciones de red
        pass
