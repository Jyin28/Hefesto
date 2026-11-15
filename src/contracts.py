"""Hefesto contracts v2 (schema_version="2.0"). Owner: Jacky.

Pure stdlib. No I/O at import. Normative source: PLAN-HEFESTO v2, section 4.
Convention: DataFrame missing = NaN; JSON missing = null (never NaN/Infinity).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2.0"
REGION_IDS = ("CR_PN", "CR_CAR")
# Región nacional (malla NASA POWER 7×7 completa) que usa la interfaz web; las pruebas BY de los dos
# sectores no la incluyen: tiene su propia familia de pruebas.
NATIONAL_REGION_ID = "CR"
WEB_REGION_IDS = REGION_IDS + (NATIONAL_REGION_ID,)
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
ANALYSIS_VERSION = "2.0"
DISCOVERY_PATH = Path(__file__).resolve().parent.parent / "config" / "discovery.json"
# Statistical configuration that is part of result identity (plan s3 items 5, 8, 11).
STATS_CONFIG = {
    "hac_lags": 3, "hac_sensitivity": [1, 5], "kernel": "bartlett", "use_t": True,
    "use_correction": True, "correction": "fdr_by", "alpha": 0.05,
    "level_thresholds": {"descriptive_min_years": 10, "inferential_min_years": 30},
}


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


@dataclass(frozen=True)
class RegionalMonthly:
    region_id: str
    variable: str
    time: str  # first day of month, ISO date (datetime64[ns] in DataFrames)
    value: float | None
    n_cells_valid: int
    n_cells_mask: int
    coverage_fraction: float


@dataclass(frozen=True)
class RegionalAnnual:
    region_id: str
    variable: str
    year: int
    value: float | None
    unit: str  # degC | mm/yr
    months_valid: int
    complete: bool


@dataclass(frozen=True)
class CellTrends:
    region_id: str
    variable: str
    lat: float
    lon: float
    start_year: int
    end_year: int
    slope_per_decade: float | None
    slope_unit: str
    p_value: float | None
    q_value: float | None
    significant: bool | None
    n_years: int
    level: str
    status: str


@dataclass(frozen=True)
class FamilyMetadata:
    family_id: str
    planned_tests: int
    valid_tests: int
    alpha: float
    method: str  # "fdr_by"
    scope: str  # "regions" | "cells"
    regions: tuple[str, ...]
    variables: tuple[str, ...]
    start_year: int
    end_year: int


@dataclass(frozen=True)
class ExportBundle:
    series_csv: bytes
    trends_csv: bytes
    provenance_json: bytes
    evidence_md: bytes
    evidence_json: bytes


def validate_query(variable: str, region_id: str | None, start_year: int, end_year: int,
                   regions: tuple[str, ...] = REGION_IDS) -> None:
    """Raise readable ValueError on invalid input; never invent a result."""
    if variable not in VARIABLE_IDS:
        raise ValueError(f"Variable invalida: {variable!r}. Validas: {', '.join(VARIABLE_IDS)}.")
    if region_id is not None and region_id not in regions:
        raise ValueError(f"Region invalida: {region_id!r}. Validas: {', '.join(regions)}.")
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


def canonical_json(obj: Any) -> str:
    """Deterministic JSON (sorted keys, no spaces) used for hashing identity."""
    return json.dumps(_clean(obj), sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_result_id(query: Any, data_sha256: str, mask_version: str,
                      stats_config: dict | None = None, code_version: str = ANALYSIS_VERSION) -> str:
    """Hash of canonical query + data checksum + mask + stats config + code version (plan 4.1).

    generated_at and hypothesis are deliberately NOT inputs: they do not change the analysis.
    """
    payload = {"query": query, "data_sha256": data_sha256, "mask_version": mask_version,
               "stats_config": STATS_CONFIG if stats_config is None else stats_config,
               "code_version": code_version}
    return sha256_hex(canonical_json(payload))[:32]


def recommend_variable(topic: str) -> dict:
    """Deterministic rule from config/discovery.json (no ranking by p). topic: heat | rain."""
    if topic not in ("heat", "rain"):
        raise ValueError(f"Tema invalido: {topic!r}. Validos: heat, rain.")
    with open(DISCOVERY_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)
    rule = next((r for r in cfg["rules"] if r["topic"] == topic), None)
    if rule is None:
        raise ValueError(f"discovery.json no define una regla para {topic!r}.")
    return {
        "schema_version": SCHEMA_VERSION,
        "topic": topic,
        "recommendation": {"variable": rule["variable"], "reason": rule["why_it_helps"],
                           "definition": rule["variable_label"], "not_measured": list(rule["not_measured"])},
        "query": {"variable": rule["variable"], "regions": list(REGION_IDS),
                  "start_year": COVERAGE_START_YEAR, "end_year": COVERAGE_END_YEAR,
                  "preset_id": rule["preset_id"]},
    }
