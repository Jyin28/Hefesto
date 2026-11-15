"""POST /api/telegram: webhook del bot. Telegram entrega aquí el /start y el /stop. Lógica en `servidor/rutas.py`."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar `servidor/` (carpeta hermana de api/)

from servidor import rutas  # noqa: E402
from servidor.respuesta import read_body, send_json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
        send_json(self, *rutas.webhook(read_body(self), secret))

    def log_message(self, *args):
        pass
