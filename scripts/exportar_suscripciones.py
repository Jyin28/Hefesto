"""Baja las suscripciones del newsletter desde Upstash Redis (Vercel) y escribe los mismos dos Excel de siempre.

En Vercel las suscripciones viven en Redis, no en `data/suscripciones/`. Este script las exporta para que el equipo las siga viendo
en Excel (`alertas_sugerencias.xlsx` y `resumen_diario.xlsx`). Esa carpeta tiene datos personales: está en `.gitignore`.

Pasos:
    cd web
    npx vercel env pull .env.local          (baja las variables del proyecto; el archivo está en .gitignore)
    cd ..
    python scripts/exportar_suscripciones.py

Las variables KV_REST_API_URL y KV_REST_API_TOKEN se leen del entorno o de `web/.env.local`. Es solo lectura: no cambia nada en Redis.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web"))

from servidor import suscripciones as remote  # noqa: E402
from servidor.store import StoreError, store_from_env  # noqa: E402
from src import newsletter  # noqa: E402


def load_env_file(path: Path) -> None:
    """Carga `KEY=valor` de un archivo (sin pisar variables ya definidas)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        key = key.strip()
        if key and not key.startswith("#") and key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


def main() -> int:
    load_env_file(ROOT / "web" / ".env.local")
    try:
        rows = remote.all_subscribers(store_from_env())
    except StoreError as error:
        print(error, file=sys.stderr)
        print("Corre `npx vercel env pull .env.local` dentro de web/ para bajar la conexión a Redis.", file=sys.stderr)
        return 1
    for kind in newsletter.KINDS:
        wanted = [{header: row.get(header, "") for header in newsletter.HEADERS} for row in rows if row["kind"] == kind]
        path = newsletter.excel_path(kind)
        newsletter.write_rows(path, sorted(wanted, key=lambda row: (row["Fecha de suscripción"], row["Usuario de Telegram"].lower())))
        print(f"{len(wanted)} suscripciones → {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
