"""Capas anuales para el mapa nacional: temperatura, lluvia, humedad y radiación UV.

Las cuatro capas comparten una misma estructura compacta para que la interfaz las trate igual:
    {label, unit, start, end, national: [valor|None], cells: {cell_id: [valor|None]}, provenance}

T2M y PRECTOTCORR salen de los JSON crudos ya verificados por `web_data.raw_payloads()`. RH2M y UV se descargan
con la misma ingesta (`ingest.fetch_variable_raw`, con caché inmutable en data/raw/), sin tocar `VARIABLE_IDS`
ni `provenance_base.json`, para no alterar la cadena de evidencia de las variables originales.
"""
from __future__ import annotations

import calendar
import math
from pathlib import Path
from typing import Any

from .ingest import fetch_variable_raw
from .regions import national_cells, national_mask_records

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

# id de la capa -> parámetro de NASA POWER, años disponibles, etiqueta y unidad.
LAYERS: dict[str, dict[str, Any]] = {
    "T2M": {"parameter": "T2M", "start": 1981, "end": 2024, "unit": "°C", "label": "Temperatura del aire a 2 m", "agg": "mean"},
    "PRECTOTCORR": {"parameter": "PRECTOTCORR", "start": 1981, "end": 2024, "unit": "mm/año",
                    "label": "Lluvia total anual", "agg": "sum_daily"},
    "RH2M": {"parameter": "RH2M", "start": 1981, "end": 2024, "unit": "%", "label": "Humedad relativa del aire a 2 m", "agg": "mean"},
    # NASA POWER solo publica el índice UV desde 2001. Es un promedio de las 24 h, no el valor del mediodía.
    "UV": {"parameter": "ALLSKY_SFC_UV_INDEX", "start": 2001, "end": 2024, "unit": "índice (promedio 24 h)",
           "label": "Radiación UV (promedio de 24 h)", "agg": "mean"},
}
DOWNLOADED = ("RH2M", "UV")


def cell_id(lat: float, lon: float) -> str:
    return f"POWER:{lat:g}:{lon:g}"


def annual_series(monthly: dict[str, Any], start: int, end: int, agg: str, fill: float = -999.0) -> list[float | None]:
    """Promedio anual ponderado por días (o total anual); `None` si el año no tiene los 12 meses válidos."""
    out: list[float | None] = []
    for year in range(start, end + 1):
        total = days = 0.0
        valid = 0
        for month in range(1, 13):
            raw = monthly.get(f"{year}{month:02d}")
            if raw is None:
                continue
            value = float(raw)
            if not math.isfinite(value) or math.isclose(value, fill) or value <= -900.0:
                continue
            n = calendar.monthrange(year, month)[1]
            total += value * n
            days += n
            valid += 1
        if valid < 12:
            out.append(None)
        elif agg == "sum_daily":
            out.append(round(total, 2))
        else:
            out.append(round(total / days, 3))
    return out


def layer_from_payload(payload: dict[str, Any], layer_id: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = LAYERS[layer_id]
    cells = national_cells()
    masks = national_mask_records()
    fill = float(payload.get("header", {}).get("fill_value", -999.0))
    points = []
    for feature in payload.get("features", []):
        lon, lat = float(feature["geometry"]["coordinates"][0]), float(feature["geometry"]["coordinates"][1])
        points.append((lat, lon, feature["properties"]["parameter"].get(spec["parameter"], {})))
    series: dict[str, list[float | None]] = {}
    resampled = False
    for cell in cells:
        # Punto de NASA más cercano al centro de la celda; empates se resuelven siempre igual (menor lat, luego lon).
        # Las capas en la malla 0,5° x 0,625° coinciden exactamente; el UV viene en 1° x 1° y varias celdas comparten punto.
        lat, lon, monthly = min(points, key=lambda p: ((p[0] - cell["lat"]) ** 2 + (p[1] - cell["lon"]) ** 2, p[0], p[1]))
        if abs(lat - cell["lat"]) > 0.5 + 1e-6 or abs(lon - cell["lon"]) > 0.5 + 1e-6:
            raise ValueError(f"La descarga de {spec['parameter']} no cubre la celda {cell_id(cell['lat'], cell['lon'])}")
        resampled = resampled or abs(lat - cell["lat"]) > 1e-4 or abs(lon - cell["lon"]) > 1e-4
        series[cell_id(cell["lat"], cell["lon"])] = annual_series(monthly, spec["start"], spec["end"], spec["agg"], fill)
    national: list[float | None] = []
    for index in range(spec["end"] - spec["start"] + 1):
        values = [(series[cell_id(m["lat"], m["lon"])][index], m["weight"]) for m in masks]
        if any(v is None for v, _ in values):
            national.append(None)
        else:
            national.append(round(sum(v * w for v, w in values) / sum(w for _, w in values), 3))
    return {"label": spec["label"], "unit": spec["unit"], "start": spec["start"], "end": spec["end"],
            "national": national, "cells": series, "resampled": resampled,
            "provenance": dict(provenance or {}, resampled=resampled)}


def build_layers(payloads: dict[str, dict[str, Any]], provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    """`payloads` trae T2M y PRECTOTCORR ya verificados; RH2M y UV se descargan o se reutilizan de data/raw/."""
    layers: dict[str, Any] = {}
    for layer_id, spec in LAYERS.items():
        if layer_id in DOWNLOADED:
            payload, meta, url, retrieved_at = fetch_variable_raw(spec["parameter"], RAW_DIR, spec["start"], spec["end"])
            info = {"source": "NASA POWER Monthly Regional API", "url": url, "sha256": meta["sha256"],
                    "retrieved_at": retrieved_at, "parameter": spec["parameter"]}
        else:
            payload = payloads[layer_id]
            info = {"source": "NASA POWER Monthly Regional API", "parameter": spec["parameter"],
                    "sha256": next((r["sha256"] for r in (provenance or {}).get("raw_files", [])
                                    if r["path"].endswith(f"{spec['parameter']}_{spec['start']}_{spec['end']}.json")), None)}
        layers[layer_id] = layer_from_payload(payload, layer_id, info)
    return layers
