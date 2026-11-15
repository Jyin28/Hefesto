"""GET /api/enviar: envío diario (alertas y resumen). Lo llama el cron de `vercel.json`. Lógica en `servidor/rutas.py`."""
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar `servidor/` (carpeta hermana de api/)

from servidor import rutas  # noqa: E402
from servidor.respuesta import send_json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, *rutas.enviar(self.headers.get("Authorization")))

    def log_message(self, *args):
        pass
