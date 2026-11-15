"""Definicion espacial y mascara terrestre fija para Costa Rica (Hefesto v2).

Propietario: Samuel.
Fuente de geometria: Centros de malla nativa NASA POWER (0.5 deg lat x 0.625 deg lon)
verificados contra la linea de costa y frontera terrestre de Costa Rica (WGS84 / EPSG:4326).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

from src.contracts import NATIONAL_REGION_ID, RegionSpec

if TYPE_CHECKING:
    import pandas as pd

MASK_VERSION = "cr-land-mask-v2.0"
MASK_SOURCE = (
    "Verificacion de centros de celda nativa NASA POWER (0.5x0.625 deg) contra "
    "limites terrestres oficiales de Costa Rica (WGS84), excluyendo celdas con centro oceanico."
)

# Cajas didacticas definidas en PLAN-HEFESTO v2 [west, south, east, north]
REGION_SPECS: dict[str, RegionSpec] = {
    "CR_PN": RegionSpec(
        id="CR_PN",
        name="Sector Pacifico Norte (entorno regional de Guanacaste)",
        lat_min=9.75,
        lat_max=11.25,
        lon_min=-86.0,
        lon_max=-85.0,
        mask_version=MASK_VERSION,
        scale_warning=(
            "Caja didactica regional (celdas ~55x69 km de reanalisis MERRA-2). "
            "No equivale a limites administrativos de Guanacaste ni a estaciones locales; "
            "las celdas costeras incluyen fraccion de superficie marina."
        ),
    ),
    "CR_CAR": RegionSpec(
        id="CR_CAR",
        name="Sector Caribe (entorno regional de Limon)",
        lat_min=9.5,
        lat_max=10.75,
        lon_min=-84.0,
        lon_max=-82.75,
        mask_version=MASK_VERSION,
        scale_warning=(
            "Caja didactica regional (celdas ~55x69 km de reanalisis MERRA-2). "
            "No equivale a limites administrativos de Limon ni a cuencas especificas; "
            "las celdas costeras incluyen fraccion de superficie marina y suavizado orografico."
        ),
    ),
}

# Centros de celda nativos (lat, lon) verificados en tierra firme dentro de cada bbox.
# Se excluyen (10.0, -85.0) [Golfo de Nicoya] y (10.5, -83.125) [Mar Caribe mar adentro].
VERIFIED_LAND_CELLS: dict[str, list[tuple[float, float]]] = {
    "CR_PN": [
        (10.0, -85.625),
        (10.5, -85.625),
        (10.5, -85.0),
        (11.0, -85.625),
        (11.0, -85.0),
    ],
    "CR_CAR": [
        (9.5, -83.75),
        (9.5, -83.125),
        (10.0, -83.75),
        (10.0, -83.125),
        (10.5, -83.75),
    ],
}


def assign_region(lat: float, lon: float) -> str | None:
    """Devuelve 'CR_PN', 'CR_CAR' o None si la celda no pertenece a las mascaras fijas."""
    for region_id, coords in VERIFIED_LAND_CELLS.items():
        for c_lat, c_lon in coords:
            if math.isclose(lat, c_lat, abs_tol=1e-4) and math.isclose(lon, c_lon, abs_tol=1e-4):
                return region_id
    return None


def mask_records() -> list[dict]:
    """Pesos cos(lat) normalizados por sector para el paquete publicado."""
    rows = []
    for region_id, coords in VERIFIED_LAND_CELLS.items():
        raw_weights = [math.cos(math.radians(lat)) for lat, _ in coords]
        total_w = sum(raw_weights)
        for (lat, lon), w in zip(coords, raw_weights):
            rows.append(
                {
                    "region_id": str(region_id),
                    "lat": float(lat),
                    "lon": float(lon),
                    "weight": float(w / total_w),
                    "mask_version": str(MASK_VERSION),
                }
            )
    return rows


def build_masks_df() -> pd.DataFrame:
    """Construye la tabla masks.parquet."""
    import pandas as pd

    df = pd.DataFrame(mask_records())
    df = df.astype(
        {
            "region_id": "string",
            "lat": "float64",
            "lon": "float64",
            "weight": "float64",
            "mask_version": "string",
        }
    )
    return df.sort_values(["region_id", "lat", "lon"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Región nacional (interfaz web): todas las celdas de la malla 7x7 que tocan territorio.
# --------------------------------------------------------------------------- #
NATIONAL_MASK_VERSION = "cr-national-cells-v1.0"
NATIONAL_CELLS_PATH = Path(__file__).resolve().parents[1] / "data" / "web" / "national_cells.json"

NATIONAL_SPEC = RegionSpec(
    id=NATIONAL_REGION_ID,
    name="Costa Rica (malla nacional NASA POWER 7x7)",
    lat_min=8.25,
    lat_max=11.75,
    lon_min=-86.5625,
    lon_max=-82.1875,
    mask_version=NATIONAL_MASK_VERSION,
    scale_warning=(
        "Promedio nacional ponderado por la fraccion de tierra de cada celda (~55x69 km de reanalisis "
        "MERRA-2). No equivale a estaciones locales ni a cantones; las celdas costeras incluyen "
        "superficie marina y los cantones usan la celda que mas los cubre."
    ),
)


def region_spec(region_id: str) -> RegionSpec:
    """Especificación de un sector o de la región nacional."""
    return NATIONAL_SPEC if region_id == NATIONAL_REGION_ID else REGION_SPECS[region_id]


def national_cells() -> list[dict]:
    """Celdas con tierra (lat, lon, land_fraction) calculadas por web/scripts/build-geo.mjs."""
    return json.loads(NATIONAL_CELLS_PATH.read_text(encoding="utf-8"))


def assign_national(lat: float, lon: float) -> str | None:
    """Devuelve 'CR' si el centro de celda es una de las celdas nacionales con tierra."""
    for cell in national_cells():
        if math.isclose(lat, cell["lat"], abs_tol=1e-4) and math.isclose(lon, cell["lon"], abs_tol=1e-4):
            return NATIONAL_REGION_ID
    return None


def national_mask_records() -> list[dict]:
    """Pesos cos(lat) x fraccion de tierra, normalizados, para el promedio nacional."""
    cells = national_cells()
    raw = [math.cos(math.radians(c["lat"])) * c["land_fraction"] for c in cells]
    total = sum(raw)
    return [
        {"region_id": NATIONAL_REGION_ID, "lat": float(c["lat"]), "lon": float(c["lon"]),
         "weight": float(w / total), "land_fraction": float(c["land_fraction"]),
         "mask_version": NATIONAL_MASK_VERSION}
        for c, w in zip(cells, raw)
    ]
