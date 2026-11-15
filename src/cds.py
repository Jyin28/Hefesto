"""Capas anuales del Copernicus Climate Data Store (CDS) para el mapa «Datos CDS».

Productos (descarga con `cdsapi`, 1981-2024, caja alrededor de Costa Rica):
  * ERA5-Land, medias mensuales, malla 0,1° x 0,1° (~11 km): temperatura, punto de rocío y lluvia.
  * ERA5, medias mensuales de niveles únicos, malla 0,25° x 0,25°: radiación UV en superficie. ERA5-Land no la publica,
    así que cada celda de 0,1° toma el punto de ERA5 más cercano a su centro (`resampled: true`).

La salida (`web/public/data/cds.json`) usa la misma forma `Layer` que `src/layers.py`, de modo que la interfaz trata igual
las capas de NASA POWER y las del CDS. No toca `snapshot.json` ni la cadena de evidencia de las variables originales.

Uso (desde la raíz de Hefesto, con una clave en ~/.cdsapirc; ver web/README.md):
    python -m src.cds
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Callable

import numpy as np

from .layers import annual_series

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "cds"
CELLS_FILE = ROOT / "data" / "web" / "cds_cells.json"
OUTPUT = ROOT / "web" / "public" / "data" / "cds.json"

START_YEAR, END_YEAR = 1981, 2024
# [norte, oeste, sur, este] con un margen de 0,1° alrededor de las celdas generadas por `npm run geo`.
AREA = [11.4, -86.1, 7.9, -82.4]
GRID_TOLERANCE = 0.06   # ERA5-Land: el centro de cada celda debe caer en un punto de la malla 0,1°.
UV_TOLERANCE = 0.13     # ERA5: el punto de 0,25° más cercano queda a lo sumo a ~0,125° por eje.

LAND = {"dataset": "reanalysis-era5-land-monthly-means", "file": "era5land_monthly_1981_2024.nc",
        "doi": "10.24381/cds.68d2bb30", "title": "ERA5-Land monthly averaged data from 1950 to present",
        "variables": ["2m_temperature", "2m_dewpoint_temperature", "total_precipitation"]}
UV = {"dataset": "reanalysis-era5-single-levels-monthly-means", "file": "era5_uv_monthly_1981_2024.nc",
      "doi": "10.24381/cds.f17050d7", "title": "ERA5 monthly averaged data on single levels from 1940 to present",
      "variables": ["downward_uv_radiation_at_the_surface"]}

ATTRIBUTION = ("Contiene información modificada del Servicio de Cambio Climático de Copernicus (C3S, 2026). "
               "ERA5-Land y ERA5 © ECMWF. Ni la Comisión Europea ni ECMWF son responsables del uso que se haga de ella.")

# Valores fuera de estos rangos casi siempre delatan un error de unidades: la capa no se publica.
PLAUSIBLE = {"T2M": (-5.0, 40.0), "PRECTOTCORR": (200.0, 15000.0), "RH2M": (20.0, 100.0), "UV": (0.5, 60.0)}
LAYER_SPECS: dict[str, dict[str, str]] = {
    "T2M": {"label": "Temperatura del aire a 2 m", "unit": "°C", "agg": "mean"},
    "PRECTOTCORR": {"label": "Lluvia total anual", "unit": "mm/año", "agg": "sum_daily"},
    "RH2M": {"label": "Humedad relativa del aire a 2 m (derivada)", "unit": "%", "agg": "mean"},
    "UV": {"label": "Radiación UV en superficie (promedio de 24 h)", "unit": "W/m²", "agg": "mean"},
}


class CdsCredentialsError(RuntimeError):
    """Falta la clave personal del CDS."""


# --- Conversiones de unidades (vectorizadas; funcionan con números, arreglos de numpy y DataArray de xarray) ---

def kelvin_to_celsius(kelvin):
    return kelvin - 273.15


def metres_to_mm(metres):
    """`total_precipitation` mensual del CDS viene en m de agua por día; 1 m = 1000 mm."""
    return metres * 1000.0


def joules_per_day_to_watts(joules_per_m2):
    """`uvb` mensual del CDS viene en J/m² por día; dividir entre 86 400 s da el promedio de 24 h en W/m²."""
    return joules_per_m2 / 86400.0


def relative_humidity(t_celsius, dewpoint_celsius):
    """Humedad relativa (%) con la fórmula de Magnus (Alduchov y Eskridge, 1996), tope 100 %.

    Se calcula con medias mensuales de T y punto de rocío, así que es una aproximación a la media mensual de la humedad.
    """
    a, b = 17.625, 243.04
    rh = 100.0 * np.exp((a * dewpoint_celsius) / (b + dewpoint_celsius) - (a * t_celsius) / (b + t_celsius))
    return np.minimum(rh, 100.0)


# --- Descarga (con caché inmutable en data/raw/cds/) ---

def credentials_available() -> bool:
    if os.environ.get("CDSAPI_KEY") or os.environ.get("CDSAPI_RC"):
        return True
    return (Path.home() / ".cdsapirc").is_file()


def _request(variables: list[str]) -> dict[str, Any]:
    return {"product_type": ["monthly_averaged_reanalysis"], "variable": variables,
            "year": [str(year) for year in range(START_YEAR, END_YEAR + 1)],
            "month": [f"{month:02d}" for month in range(1, 13)], "time": ["00:00"],
            "data_format": "netcdf", "download_format": "unarchived", "area": AREA}


def fetch_product(product: dict[str, Any], raw_dir: Path = RAW_DIR, client_factory: Callable[[], Any] | None = None,
                  optional: bool = False) -> tuple[Path, dict[str, Any]] | None:
    """Devuelve (ruta del .nc, metadatos). Si el archivo ya está en caché no se vuelve a pedir al CDS.

    Un producto `optional` (el UV) **nunca se descarga solo**: sin archivo devuelve `None` y la capa que depende de él
    no se publica. Así tener una clave del CDS no dispara solicitudes que nadie pidió.
    """
    target = raw_dir / product["file"]
    meta_path = target.with_suffix(".meta.json")
    if target.is_file() and meta_path.is_file():
        return target, json.loads(meta_path.read_text(encoding="utf-8"))
    if target.is_file():
        # Archivo descargado a mano desde la web del CDS: se registra su huella y se usa sin pedirlo otra vez.
        meta = {"dataset": product["dataset"], "title": product["title"], "doi": product["doi"],
                "url": f"https://cds.climate.copernicus.eu/datasets/{product['dataset']}", "request": None,
                "downloaded_manually": True, "sha256": sha256(target.read_bytes()).hexdigest(),
                "retrieved_at": datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target, meta
    if optional:
        return None
    if client_factory is None:
        if not credentials_available():
            raise CdsCredentialsError(
                "No hay clave del CDS. Creá una cuenta en https://cds.climate.copernicus.eu, aceptá la licencia de "
                f"«{product['title']}» y guardá tu clave en {Path.home() / '.cdsapirc'} "
                "(url: https://cds.climate.copernicus.eu/api y key: <tu token>).")
        import cdsapi
        client_factory = cdsapi.Client
    raw_dir.mkdir(parents=True, exist_ok=True)
    request = _request(product["variables"])
    partial = target.with_suffix(".nc.part")
    print(f"Pidiendo {product['dataset']} al CDS (puede tardar varios minutos en la cola)…", file=sys.stderr)
    client_factory().retrieve(product["dataset"], request, str(partial))
    digest = sha256(partial.read_bytes()).hexdigest()
    partial.replace(target)
    meta = {"dataset": product["dataset"], "title": product["title"], "doi": product["doi"],
            "url": f"https://cds.climate.copernicus.eu/datasets/{product['dataset']}", "request": request,
            "sha256": digest, "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target, meta


def open_dataset(path: Path):
    """Abre un NetCDF del CDS (o un zip con varios) y lo deja en memoria con `time`, `latitude` y `longitude` estándar."""
    import xarray as xr

    def load(file: Path):
        with xr.open_dataset(file) as handle:
            return handle.load()

    if zipfile.is_zipfile(path):
        with TemporaryDirectory() as folder, zipfile.ZipFile(path) as archive:
            archive.extractall(folder)
            parts = [load(file) for file in sorted(Path(folder).glob("*.nc"))]
        dataset = xr.merge(parts, compat="override")
    else:
        dataset = load(path)
    if "valid_time" in dataset.dims and "time" not in dataset.dims:
        dataset = dataset.rename({"valid_time": "time"})
    if "expver" in dataset.dims:  # ERA5T reciente: se combinan las dos versiones.
        dataset = dataset.mean("expver", skipna=True)
    extras = [name for name in ("number", "expver") if name in dataset.coords and name not in dataset.dims]
    return dataset.reset_coords(extras, drop=True) if extras else dataset


# --- Procesamiento ---

def load_cells(path: Path = CELLS_FILE) -> list[dict[str, Any]]:
    """Celdas ERA5-Land con tierra generadas por `npm run geo` (mismo id que usa la interfaz)."""
    cells = json.loads(path.read_text(encoding="utf-8-sig"))
    return [dict(cell, id=f"ERA5L:{cell['lat']:g}:{cell['lon']:g}") for cell in cells]


def _monthly_by_cell(data, cells: list[dict[str, Any]], tolerance: float) -> tuple[Any, bool]:
    """Valores mensuales (tiempo x celda) en el punto de malla más cercano al centro de cada celda."""
    import xarray as xr

    lats = xr.DataArray([cell["lat"] for cell in cells], dims="cell")
    lons = xr.DataArray([cell["lon"] for cell in cells], dims="cell")
    try:
        picked = data.sel(latitude=lats, longitude=lons, method="nearest", tolerance=tolerance)
    except KeyError as error:
        raise ValueError("La descarga del CDS no cubre todas las celdas del mapa; revisá la caja AREA.") from error
    resampled = bool((abs(picked["latitude"].values - lats.values) > 1e-4).any()
                     or (abs(picked["longitude"].values - lons.values) > 1e-4).any())
    return picked, resampled


def _annual_layer(picked, cells: list[dict[str, Any]], layer_id: str) -> tuple[dict[str, list[float | None]], list[float | None]]:
    spec = LAYER_SPECS[layer_id]
    years, months = picked["time"].dt.year.values, picked["time"].dt.month.values
    values = picked.transpose("time", "cell").values
    series: dict[str, list[float | None]] = {}
    for index, cell in enumerate(cells):
        monthly = {f"{int(y)}{int(m):02d}": float(values[row, index]) for row, (y, m) in enumerate(zip(years, months))}
        series[cell["id"]] = annual_series(monthly, START_YEAR, END_YEAR, spec["agg"])
    national: list[float | None] = []
    for position in range(END_YEAR - START_YEAR + 1):
        pairs = [(series[cell["id"]][position], math.cos(math.radians(cell["lat"])) * cell["land_fraction"]) for cell in cells]
        pairs = [(value, weight) for value, weight in pairs if value is not None]
        national.append(round(sum(v * w for v, w in pairs) / sum(w for _, w in pairs), 3) if pairs else None)
    return series, national


def check_plausible(layer_id: str, series: dict[str, list[float | None]]) -> None:
    low, high = PLAUSIBLE[layer_id]
    values = [value for cell in series.values() for value in cell if value is not None]
    if not values:
        raise ValueError(f"La capa {layer_id} quedó sin datos válidos.")
    if min(values) < low or max(values) > high:
        raise ValueError(f"La capa {layer_id} tiene valores fuera de lo plausible ({min(values):g} a {max(values):g}, "
                         f"esperado {low:g} a {high:g}); posible error de unidades. No se publica.")


def build_layers(land, uv, cells: list[dict[str, Any]], land_meta: dict[str, Any],
                 uv_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capas con la forma `Layer` de la interfaz. `land` y `uv` son Dataset de xarray ya normalizados.

    `uv` puede ser `None` (todavía no hay archivo de ERA5): entonces no se genera la capa `UV`.
    """
    t_celsius = kelvin_to_celsius(land["t2m"])
    layers_data = {
        "T2M": (t_celsius, land_meta, GRID_TOLERANCE, "2m_temperature"),
        "PRECTOTCORR": (metres_to_mm(land["tp"]), land_meta, GRID_TOLERANCE, "total_precipitation"),
        "RH2M": (relative_humidity(t_celsius, kelvin_to_celsius(land["d2m"])), land_meta, GRID_TOLERANCE,
                 "2m_temperature + 2m_dewpoint_temperature (Magnus)"),
    }
    if uv is not None and uv_meta is not None:
        layers_data["UV"] = (joules_per_day_to_watts(uv["uvb"]), uv_meta, UV_TOLERANCE, "downward_uv_radiation_at_the_surface")
    layers: dict[str, Any] = {}
    for layer_id, (data, meta, tolerance, parameter) in layers_data.items():
        picked, resampled = _monthly_by_cell(data, cells, tolerance)
        series, national = _annual_layer(picked, cells, layer_id)
        check_plausible(layer_id, series)
        spec = LAYER_SPECS[layer_id]
        layers[layer_id] = {
            "label": spec["label"], "unit": spec["unit"], "start": START_YEAR, "end": END_YEAR,
            "national": national, "cells": series, "resampled": resampled,
            "provenance": {"source": meta["title"], "url": meta["url"], "doi": meta["doi"], "sha256": meta["sha256"],
                           "retrieved_at": meta["retrieved_at"], "parameter": parameter, "resampled": resampled},
        }
    return layers


def write_output(payload: dict[str, Any], target: Path = OUTPUT) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    with NamedTemporaryFile(dir=target.parent, mode="w", encoding="utf-8", delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(content)
            output.close()
            temporary.replace(target)
        finally:
            output.close()
            temporary.unlink(missing_ok=True)


def export_cds(raw_dir: Path = RAW_DIR, cells_file: Path = CELLS_FILE, target: Path = OUTPUT,
               client_factory: Callable[[], Any] | None = None, download_uv: bool = False) -> dict[str, Any]:
    """ERA5-Land es obligatorio (se descarga si falta). El UV de ERA5 solo se usa si su archivo está en `raw_dir`
    o si se pide `download_uv=True`; sin él, la capa UV no se publica."""
    cells = load_cells(cells_file)
    land_path, land_meta = fetch_product(LAND, raw_dir, client_factory)
    uv_found = fetch_product(UV, raw_dir, client_factory, optional=not download_uv)
    uv_path, uv_meta = uv_found if uv_found else (None, None)
    layers = build_layers(open_dataset(land_path), open_dataset(uv_path) if uv_path else None, cells, land_meta, uv_meta)
    keys = ("dataset", "title", "doi", "url")
    products = {"land": {key: land_meta[key] for key in keys}}
    if uv_meta:
        products["uv"] = {key: uv_meta[key] for key in keys}
    payload = {"layers": layers, "attribution": ATTRIBUTION, "products": products}
    write_output(payload, target)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera web/public/data/cds.json con los datos del Copernicus CDS.")
    parser.add_argument("--download-uv", action="store_true",
                        help="Descargar también el UV de ERA5 desde el CDS si no está en data/raw/cds/ (necesita ~/.cdsapirc). "
                             "Sin esta opción, el UV solo se usa si su archivo ya está.")
    args = parser.parse_args(argv)
    try:
        payload = export_cds(download_uv=args.download_uv)
    except CdsCredentialsError as error:
        print(error, file=sys.stderr)
        return 2
    for layer_id, layer in payload["layers"].items():
        usable = sum(value is not None for value in layer["national"])
        with_data = sum(any(value is not None for value in series) for series in layer["cells"].values())
        print(f"{layer_id}: {with_data}/{len(layer['cells'])} celdas con dato, "
              f"{usable}/{len(layer['national'])} años con promedio nacional")
    if "UV" not in payload["layers"]:
        print("Sin archivo ERA5 de UV: la capa UV no se publica (el botón UV se desactiva en «Datos CDS»).", file=sys.stderr)
    print(f"Escrito {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
