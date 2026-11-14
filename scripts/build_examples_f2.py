"""Build the F2 example bundles for Kevin: docs/jacky/examples/<case>/ (J2.6).

Reproducible: the mock clocks are pinned, so running this twice gives identical files.
Everything is synthetic mock output. Usage (repo root): python scripts/build_examples_f2.py
"""
from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import service_mock_f2 as m  # noqa: E402
from src.contracts_ext import AnalysisQuery  # noqa: E402
from src.export_f2 import build_export  # noqa: E402

OUT = ROOT / "docs" / "jacky" / "examples"
PIN_DATE = date(2026, 11, 14)
PIN_NOW = "2026-11-14T00:00:00Z"


def hist(zone, **kw):
    return AnalysisQuery("historical", "T2M", zone_ids=(zone,), start_date="2000-01-01",
                         end_date="2009-12-31", **kw)


def fc(zone):
    return AnalysisQuery("forecast", "T2M", zone_ids=(zone,), start_date="2025-01-01", end_date="2025-06-30")


def water(product, zone):
    return AnalysisQuery(product, None, zone_ids=(zone,), start_date="2024-01-01", end_date="2024-06-30")


def event(**kw):
    return AnalysisQuery("event", "PRECTOTCORR", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98", **kw)


CASES = [
    ("01_historical_available", lambda: m.get_series(hist("CR_PN"))),
    ("02_historical_partial", lambda: m.get_series(AnalysisQuery("historical", "T2M", zone_ids=("MOCK_PARTIAL",)))),
    ("03_historical_unavailable", lambda: m.get_series(hist("MOCK_NODATA"))),
    ("04_historical_error", lambda: m.get_series(hist("MOCK_ERROR"))),
    ("05_historical_unsupported", lambda: m.get_series(hist("CR_PN", time_resolution="daily"))),
    ("06_historical_stale", lambda: m.get_series(hist("MOCK_STALE"))),
    ("07_map_cells", lambda: m.get_map(AnalysisQuery("historical", "T2M", zone_ids=("CR_PN",), metric="slope"))),
    ("08_event_available", lambda: m.get_event_series(event())),
    ("09_event_short_baseline", lambda: m.get_event_series(event(baseline="1981-1990"))),
    ("10_forecast_validated", lambda: m.get_local_forecast(fc("CR_PN"))),
    ("11_forecast_not_validated", lambda: m.get_local_forecast(fc("CR_CAR"))),
    ("12_water_distribution", lambda: m.get_water_distribution(water("water_distribution", "CR_PN"))),
    ("13_service_coverage_partial", lambda: m.get_service_coverage(water("service_coverage", "CR_CAR"))),
    ("14_capabilities", lambda: m.get_capabilities(hist("CR_PN"))),
]


def main() -> None:
    m._today = lambda: PIN_DATE
    m._now = lambda: PIN_NOW
    if OUT.exists():
        shutil.rmtree(OUT)
    rows = []
    for name, fn in CASES:
        resp = fn()
        files = build_export(resp, generated_at=PIN_NOW)
        d = OUT / name
        d.mkdir(parents=True)
        for fname, data in files.items():
            (d / fname).write_bytes(data)
        a = resp.availability
        rows.append((name, resp.product, a.status, a.reason_code or "-", ", ".join(sorted(files))))
    lines = ["# Ejemplos F2 para Kevin (J2.6)", "",
             "Salida del mock sintetico, reproducible con `python scripts/build_examples_f2.py` "
             "(relojes fijados a 2026-11-14). Cada carpeta es un export completo: `manifest.json` lista "
             "tablas presentes y ausentes; `evidence.json` es la ficha; `ficha.md` es su version legible.", "",
             "| Caso | Producto | Estado | Razon | Archivos |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {p} | {s} | {r} | {f} |" for n, p, s, r, f in rows]
    lines += ["", "Convenciones CSV: UTF-8, coma, punto decimal, ausente = celda vacia, anidados = JSON compacto, "
              "booleanos true/false. Cada fila lleva `result_id` y `product` mas su clave de union. "
              "Un producto sin datos no genera CSV: aparece en `tables_absent` con su razon.", ""]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(CASES)} casos escritos en {OUT}")


if __name__ == "__main__":
    main()
