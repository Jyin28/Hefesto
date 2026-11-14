"""Hefesto contracts v2 (schema_version="2.0"). Owner: Jacky.

Pure stdlib. No I/O at import. Normative source: PLAN-HEFESTO v2, section 4.
Convention: DataFrame missing = NaN; JSON missing = null (never NaN/Infinity).
"""
from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "2.0"
REGION_IDS = ("CR_PN", "CR_CAR")
VARIABLE_IDS = ("T2M", "PRECTOTCORR")
PRESET_IDS = ("CR_HEAT", "CR_RAIN")
LEVELS = ("none", "descriptive", "inferential")
STATUSES = ("ok", "insufficient_data", "fit_failed")
SLOPE_UNITS = {"T2M": "degC/decade", "PRECTOTCORR": "mm/yr/decade"}
ANNUAL_UNITS = {"T2M": "degC", "PRECTOTCORR": "mm/yr"}
MONTHLY_UNITS = {"T2M": "degC", "PRECTOTCORR": "mm/day"}  # [verificar] metadatos
# Inclusive data coverage target [verificar] against real API response.
COVERAGE_START_YEAR = 1981
COVERAGE_END_YEAR = 2024


@dataclass(frozen=True)
class VariableInfo:
    id: str
    label: str
    definition: str
    unit_monthly: str
    unit_annual: str
    source_id: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class RegionSpec:
    """Bounding box in WGS84 degrees. Plan bbox order is [west,south,east,north]."""

    id: str
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    mask_version: str
    scale_warning: str

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(west, south, east, north)."""
        return (self.lon_min, self.lat_min, self.lon_max, self.lat_max)


@dataclass(frozen=True)
class QueryParams:
    variable: str
    regions: tuple[str, str]
    start_year: int
    end_year: int
    preset_id: str  # "CR_HEAT" | "CR_RAIN"


@dataclass(frozen=True)
class TrendResult:
    """All fields mandatory; optional values are None (null in JSON)."""

    region_id: str
    variable: str
    start_year: int
    end_year: int
    first_used_year: int | None
    last_used_year: int | None
    n_years: int
    level: str  # none | descriptive | inferential
    status: str  # ok | insufficient_data | fit_failed
    slope_per_decade: float | None
    slope_unit: str  # degC/decade | mm/yr/decade
    total_change: float | None
    ci_low: float | None
    ci_high: float | None
    se_hac: float | None
    p_value: float | None
    p_adjusted: float | None
    significant: bool | None
    family_id: str | None
    hac_lags: int | None
    method: str
    coverage_fraction: float
    warnings: tuple[str, ...]


def validate_query(variable: str, region_id: str | None, start_year: int, end_year: int) -> None:
    """Raise readable ValueError on invalid input; never invent a result."""
    if variable not in VARIABLE_IDS:
        raise ValueError(f"Variable invalida: {variable!r}. Validas: {', '.join(VARIABLE_IDS)}.")
    if region_id is not None and region_id not in REGION_IDS:
        raise ValueError(f"Region invalida: {region_id!r}. Validas: {', '.join(REGION_IDS)}.")
    for name, y in (("start_year", start_year), ("end_year", end_year)):
        if isinstance(y, bool) or not isinstance(y, int):
            raise ValueError(f"{name} debe ser entero, recibido {y!r}.")
    if start_year > end_year:
        raise ValueError(f"Periodo invalido: start_year {start_year} > end_year {end_year}.")
    if start_year < COVERAGE_START_YEAR or end_year > COVERAGE_END_YEAR:
        raise ValueError(
            f"Periodo {start_year}-{end_year} fuera de cobertura "
            f"{COVERAGE_START_YEAR}-{COVERAGE_END_YEAR} (inclusive)."
        )


def _clean(obj: Any) -> Any:
    """Recursively map NaN/Infinity to None, tuples to lists, dataclasses to dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _clean(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def to_jsonable(obj: Any) -> Any:
    return _clean(obj)


def to_json(obj: Any, **kwargs: Any) -> str:
    """Strict JSON: NaN/Infinity become null; allow_nan=False enforces it."""
    return json.dumps(_clean(obj), allow_nan=False, ensure_ascii=False, **kwargs)
