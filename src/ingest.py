"""Ingesta reproducible desde NASA POWER Monthly Regional API (Hefesto v2).

Propietario: Samuel.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.contracts import COVERAGE_END_YEAR, COVERAGE_START_YEAR, MONTHLY_UNITS, VARIABLE_IDS
from src.regions import MASK_VERSION, assign_region

# Caja minima valida para el endpoint regional (>= 2 deg x 2 deg) que envuelve CR_PN y CR_CAR
DOWNLOAD_BBOX = {
    "lon_min": -86.5,
    "lon_max": -82.5,
    "lat_min": 8.5,
    "lat_max": 11.5,
}

BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"
SOURCE_PAGE = "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_request_url(variable: str, start_year: int, end_year: int) -> str:
    return (
        f"{BASE_URL}"
        f"?parameters={variable}"
        f"&community=AG"
        f"&longitude-min={DOWNLOAD_BBOX['lon_min']}&longitude-max={DOWNLOAD_BBOX['lon_max']}"
        f"&latitude-min={DOWNLOAD_BBOX['lat_min']}&latitude-max={DOWNLOAD_BBOX['lat_max']}"
        f"&start={start_year}&end={end_year}"
        f"&format=JSON"
    )


def fetch_variable_raw(
    variable: str,
    raw_dir: Path,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
    retries: int = 3,
    pause_sec: float = 2.0,
) -> tuple[dict[str, Any], dict[str, str], str, str]:
    """Descarga o reutiliza cache raw inmutable para una variable."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / f"nasa_power_monthly_{variable}_{start_year}_{end_year}.json"
    url = build_request_url(variable, start_year, end_year)

    if raw_file.exists():
        raw_bytes = raw_file.read_bytes()
        retrieved_at = datetime.fromtimestamp(
            raw_file.stat().st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        last_err: Exception | None = None
        raw_bytes = b""
        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    raw_bytes = resp.read()
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
                if attempt < retries:
                    time.sleep(pause_sec * attempt)
        if not raw_bytes:
            raise RuntimeError(f"Fallo descarga NASA POWER para {variable}: {last_err}")

        raw_file.write_bytes(raw_bytes)
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = json.loads(raw_bytes.decode("utf-8"))
    file_meta = {
        "path": f"data/raw/{raw_file.name}",
        "sha256": sha256_bytes(raw_bytes),
    }
    return payload, file_meta, url, retrieved_at


def parse_payload_to_rows(payload: dict[str, Any], variable: str) -> list[dict[str, Any]]:
    """Convierte el GeoJSON de NASA POWER a filas mensuales limpias de Costa Rica."""
    fill_value = float(payload.get("header", {}).get("fill_value", -999.0))
    unit = MONTHLY_UNITS[variable]
    rows: list[dict[str, Any]] = []

    for feat in payload.get("features", []):
        coords = feat["geometry"]["coordinates"]
        lon = float(coords[0])
        lat = float(coords[1])
        region_id = assign_region(lat, lon)
        if region_id is None:
            continue

        series = feat["properties"]["parameter"].get(variable, {})
        for ym_key, raw_val in series.items():
            # Descartar claves anuales como '198113' o 'ANN'
            if len(ym_key) != 6 or not ym_key.isdigit():
                continue
            year = int(ym_key[:4])
            month = int(ym_key[4:6])
            if month < 1 or month > 12:
                continue

            val = float(raw_val)
            if np.isclose(val, fill_value) or val <= -900.0:
                val = np.nan

            rows.append(
                {
                    "region_id": region_id,
                    "variable": variable,
                    "lat": lat,
                    "lon": lon,
                    "time": pd.Timestamp(year=year, month=month, day=1),
                    "value": val,
                    "unit": unit,
                    "synthetic": False,
                }
            )
    return rows


def ingest_all(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Descarga y normaliza todas las variables del MVP y construye provenance_base."""
    all_rows: list[dict[str, Any]] = []
    request_urls: list[str] = []
    raw_files: list[dict[str, str]] = []
    retrieved_timestamps: list[str] = []
    api_version: str | None = None

    for var in VARIABLE_IDS:
        payload, file_meta, url, retrieved_at = fetch_variable_raw(var, raw_dir)
        if api_version is None:
            api_version = payload.get("header", {}).get("api", {}).get("version")
        request_urls.append(url)
        raw_files.append(file_meta)
        retrieved_timestamps.append(retrieved_at)
        all_rows.extend(parse_payload_to_rows(payload, var))

    df = pd.DataFrame(all_rows)
    df = df.astype(
        {
            "region_id": "string",
            "variable": "string",
            "lat": "float64",
            "lon": "float64",
            "datetime64[ns]" if False else "time": "datetime64[ns]",
            "value": "float64",
            "unit": "string",
            "synthetic": "bool",
        }
    )
    # Deduplicar clave primaria por seguridad
    df = (
        df.drop_duplicates(subset=["region_id", "variable", "lat", "lon", "time"])
        .sort_values(["region_id", "variable", "lat", "lon", "time"])
        .reset_index(drop=True)
    )

    provenance = {
        "provider": "NASA POWER (MERRA-2 assimilation)",
        "source_page": SOURCE_PAGE,
        "request_urls": request_urls,
        "retrieved_at": max(retrieved_timestamps),
        "provider_version": None,  # Desconocida en API; no confundir con api_version
        "api_version": api_version,
        "native_resolution_deg": [0.5, 0.625],
        "raw_files": raw_files,
        "transformations": [
            "Descarga regional minima [-86.5, 8.5, -82.5, 11.5] para cumplir umbral >=2x2 deg de API.",
            "Filtrado estricto a celdas terrestres verificadas dentro de CR_PN y CR_CAR.",
            "Exclusion de registros anuales (mes 13 / ANN) conservando solo meses 01..12.",
            "Conversion de fill_value (-999.0) a NaN y normalizacion de unidades a degC y mm/day.",
            "Deduplicacion por clave primaria (region_id, variable, lat, lon, time).",
        ],
        "mask_version": MASK_VERSION,
        "synthetic": False,
    }
    return df, provenance