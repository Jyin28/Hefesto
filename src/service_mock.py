"""Hefesto MOCK service. Development tool ONLY: every output is synthetic=True.

Numbers here are deterministic contract examples, NOT scientific evidence and NOT
NASA data. Inference fields (se/p/CI) at level "inferential" are PLACEHOLDERS, not
a real OLS+HAC fit. Real service (src/service.py) is not implemented yet and must
never silently fall back to this module.

F1 scope: list_variables, list_regions, get_coverage, get_annual_series,
get_trend, get_comparison. Pending (F2, raise NotImplementedError):
get_cell_trends, get_event_view, build_provenance, build_evidence_card.
No I/O at import.
"""
from __future__ import annotations

import math

from .contracts import (
    ANNUAL_UNITS,
    COVERAGE_END_YEAR,
    COVERAGE_START_YEAR,
    MONTHLY_UNITS,
    REGION_IDS,
    SCHEMA_VERSION,
    SLOPE_UNITS,
    VARIABLE_IDS,
    RegionSpec,
    TrendResult,
    VariableInfo,
    to_jsonable,
    validate_query,
)

SYNTHETIC = True
MOCK_METHOD_DESCRIPTIVE = "OLS descriptivo (MOCK sintetico)"
MOCK_METHOD_INFERENTIAL = "OLS+HAC L=3 (MOCK: se/p/IC son marcadores, no un ajuste real)"
MASK_VERSION = "mock"
FAMILY_ALPHA = 0.05

# Synthetic generator parameters: (base value, true slope per year, wiggle amplitude, se factor)
_PARAMS = {
    ("CR_PN", "T2M"): (26.0, 0.030, 0.25, 0.30),
    ("CR_CAR", "T2M"): (25.0, 0.020, 0.25, 0.80),
    ("CR_PN", "PRECTOTCORR"): (1800.0, -4.0, 120.0, 0.60),
    ("CR_CAR", "PRECTOTCORR"): (3300.0, 5.0, 200.0, 2.50),
}

_VARIABLES = (
    VariableInfo(
        id="T2M",
        label="Temperatura del aire a 2 m",
        definition="Temperatura media del aire a 2 metros sobre la superficie (estimacion de reanalisis).",
        unit_monthly=MONTHLY_UNITS["T2M"],
        unit_annual=ANNUAL_UNITS["T2M"],
        source_id="S1",
        limitations=("Estimacion de modelo con asimilacion, no medicion directa", "Resolucion ~0,5 x 0,625 grados"),
    ),
    VariableInfo(
        id="PRECTOTCORR",
        label="Precipitacion corregida",
        definition="Tasa de precipitacion corregida; la anual es la suma de tasa mensual x dias.",
        unit_monthly=MONTHLY_UNITS["PRECTOTCORR"],
        unit_annual=ANNUAL_UNITS["PRECTOTCORR"],
        source_id="S1",
        limitations=("No mide caudal, humedad de suelo ni recarga", "Resolucion ~0,5 x 0,625 grados"),
    ),
)

_REGIONS = (
    RegionSpec("CR_PN", "Sector Pacifico Norte, entorno regional de Guanacaste", 9.75, 11.25, -86.0, -85.0,
               MASK_VERSION, "Ventana didactica; celdas de decenas de km, no limite administrativo."),
    RegionSpec("CR_CAR", "Sector Caribe, entorno regional de Limon", 9.5, 10.75, -84.0, -82.75,
               MASK_VERSION, "Ventana didactica; celdas de decenas de km, no limite administrativo."),
)


def list_variables() -> list[VariableInfo]:
    return list(_VARIABLES)


def list_regions() -> list[RegionSpec]:
    return list(_REGIONS)


def get_coverage() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "synthetic": SYNTHETIC,
        "start_year": COVERAGE_START_YEAR,
        "end_year": COVERAGE_END_YEAR,
        "regions": list(REGION_IDS),
        "variables": list(VARIABLE_IDS),
        "mask_version": MASK_VERSION,
    }


def _synthetic_value(region_id: str, variable: str, year: int) -> float:
    base, slope, amp, _ = _PARAMS[(region_id, variable)]
    wiggle = amp * math.sin(2.0 * year)  # deterministic, no RNG
    return round(base + slope * (year - COVERAGE_START_YEAR) + wiggle, 6)


def get_annual_series(variable: str, region_id: str, start_year: int, end_year: int) -> list[dict]:
    """RegionalAnnual rows (plus mock-only key synthetic=True). Years inclusive."""
    validate_query(variable, region_id, start_year, end_year)
    return [
        {
            "region_id": region_id,
            "variable": variable,
            "year": y,
            "value": _synthetic_value(region_id, variable, y),
            "unit": ANNUAL_UNITS[variable],
            "months_valid": 12,
            "complete": True,
            "synthetic": SYNTHETIC,
        }
        for y in range(start_year, end_year + 1)
    ]


def _ols_slope(years: list[int], values: list[float]) -> float:
    n = len(years)
    mx = sum(years) / n
    my = sum(values) / n
    sxx = sum((x - mx) ** 2 for x in years)
    return sum((x - mx) * (y - my) for x, y in zip(years, values)) / sxx


def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def _raw_trend(variable: str, region_id: str, start_year: int, end_year: int) -> TrendResult:
    n = end_year - start_year + 1
    unit = SLOPE_UNITS[variable]
    base_warnings = ["synthetic"]
    if n < 10:
        return TrendResult(region_id, variable, start_year, end_year, None, None, n, "none",
                           "insufficient_data", None, unit, None, None, None, None, None, None, None,
                           None, None, "sin ajuste (n<10)", 1.0, tuple(base_warnings + ["short_record"]))
    rows = get_annual_series(variable, region_id, start_year, end_year)
    years = [r["year"] for r in rows]
    b = _ols_slope(years, [r["value"] for r in rows])
    slope_dec = round(10.0 * b, 6)
    total = round(b * (years[-1] - years[0]), 6)
    if n < 30:
        return TrendResult(region_id, variable, start_year, end_year, years[0], years[-1], n,
                           "descriptive", "ok", slope_dec, unit, total, None, None, None, None, None, None,
                           None, None, MOCK_METHOD_DESCRIPTIVE, 1.0, tuple(base_warnings + ["short_record"]))
    factor = _PARAMS[(region_id, variable)][3]
    se = round(max(abs(slope_dec) * factor, 1e-9), 6)
    p = _normal_two_sided_p(slope_dec / se)
    return TrendResult(region_id, variable, start_year, end_year, years[0], years[-1], n,
                       "inferential", "ok", slope_dec, unit, total,
                       round(slope_dec - 1.96 * se, 6), round(slope_dec + 1.96 * se, 6), se,
                       p, None, None, None, 3, MOCK_METHOD_INFERENTIAL, 1.0,
                       tuple(base_warnings + ["mock_inference_placeholder"]))


def _by_adjust(pvals: list[float]) -> list[float]:
    """Benjamini-Yekutieli adjusted p-values (same order as input)."""
    m = len(pvals)
    if m == 0:
        return []
    c = sum(1.0 / k for k in range(1, m + 1))
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvals[i] * m * c / rank)
        adj[i] = min(running, 1.0)
    return adj


def family_id(start_year: int, end_year: int) -> str:
    return f"regions|T2M+PRECTOTCORR|CR_PN+CR_CAR|{start_year}-{end_year}|v2"


def _family(start_year: int, end_year: int) -> tuple[list[TrendResult], dict]:
    """Full regional family (2 variables x 2 regions) BEFORE any view filtering."""
    raw = [_raw_trend(v, r, start_year, end_year) for v in VARIABLE_IDS for r in REGION_IDS]
    valid_idx = [i for i, t in enumerate(raw) if t.p_value is not None]
    adj = _by_adjust([raw[i].p_value for i in valid_idx])
    fid = family_id(start_year, end_year)
    out = list(raw)
    for i, q in zip(valid_idx, adj):
        out[i] = TrendResult(**{**raw[i].__dict__, "p_adjusted": q, "significant": q < FAMILY_ALPHA,
                                "family_id": fid})
    meta = {
        "family_id": fid,
        "planned_tests": len(raw),
        "valid_tests": len(valid_idx),
        "alpha": FAMILY_ALPHA,
        "method": "fdr_by",
        "scope": "regions",
        "regions": list(REGION_IDS),
        "variables": list(VARIABLE_IDS),
        "start_year": start_year,
        "end_year": end_year,
    }
    return out, meta


def get_trend(variable: str, region_id: str, start_year: int, end_year: int) -> TrendResult:
    validate_query(variable, region_id, start_year, end_year)
    results, _ = _family(start_year, end_year)
    return next(t for t in results if t.variable == variable and t.region_id == region_id)


def get_comparison(variable: str, start_year: int, end_year: int,
                   regions: tuple[str, ...] = ("CR_PN", "CR_CAR")) -> dict:
    validate_query(variable, None, start_year, end_year)
    for r in regions:
        validate_query(variable, r, start_year, end_year)
    results, meta = _family(start_year, end_year)
    return {
        "schema_version": SCHEMA_VERSION,
        "synthetic": SYNTHETIC,
        "variable": variable,
        "start_year": start_year,
        "end_year": end_year,
        "results": [to_jsonable(t) for t in results if t.variable == variable and t.region_id in regions],
        "family_metadata": [meta],
    }


_PENDING = "{} pendiente (F2): el mock aun no lo implementa."


def get_cell_trends(variable, region_id, start_year, end_year):
    raise NotImplementedError(_PENDING.format("get_cell_trends"))


def get_event_view(variable):
    raise NotImplementedError(_PENDING.format("get_event_view (P1)"))


def build_provenance(query):
    raise NotImplementedError(_PENDING.format("build_provenance"))


def build_evidence_card(query, hypothesis: str = ""):
    raise NotImplementedError(_PENDING.format("build_evidence_card"))
