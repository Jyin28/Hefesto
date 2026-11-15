"""AguaAlerta MOCK service. Development tool ONLY: every output is synthetic=True.

Numbers here are deterministic contract examples, NOT scientific evidence and NOT
NASA data. Inference fields (se/p/CI) at level "inferential" are PLACEHOLDERS, not
a real OLS+HAC fit. Real service (src/service.py) is not implemented yet and must
never silently fall back to this module.

F1 scope: list_variables, list_regions, get_coverage, get_annual_series,
get_trend, get_comparison, get_cell_trends, build_provenance, build_evidence_card,
plus fit_mock_trend for edge cases. Pending (raises NotImplementedError): get_event_view (P1).
No I/O at import.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from .contracts import (
    ANALYSIS_VERSION,
    PRESET_IDS,
    STATS_CONFIG,
    CellTrends,
    FamilyMetadata,
    QueryParams,
    canonical_json,
    compute_result_id,
    sha256_hex,
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


MIN_COVERAGE = 0.8  # plan s3 item 1: >=80 % of candidate land weight


def fit_mock_trend(rows, region_id, variable, start_year, end_year, coverage_fraction=1.0):
    """MOCK fit over (year, value|None) rows. Covers plan s3 items 1, 5, 6, 13.

    Years are never compressed: gaps keep the real year axis, make the slope descriptive and
    set inferential fields to null with warning temporal_gaps. Inference fields are placeholders.
    """
    unit = SLOPE_UNITS[variable]
    w = ["synthetic"]
    valid = sorted((y, v) for y, v in rows if v is not None)
    n = len(valid)
    if coverage_fraction < MIN_COVERAGE:
        return TrendResult(region_id, variable, start_year, end_year, None, None, n, "none",
                           "insufficient_data", None, unit, None, None, None, None, None, None, None,
                           None, None, "sin ajuste (cobertura insuficiente)", coverage_fraction,
                           tuple(w + ["coverage_failure"]))
    if n < 10:
        return TrendResult(region_id, variable, start_year, end_year, None, None, n, "none",
                           "insufficient_data", None, unit, None, None, None, None, None, None, None,
                           None, None, "sin ajuste (n<10)", coverage_fraction, tuple(w + ["short_record"]))
    years = [y for y, _ in valid]
    vals = [v for _, v in valid]
    b = _ols_slope(years, vals)
    slope_dec = round(10.0 * b, 6)
    total = round(b * (years[-1] - years[0]), 6)
    gaps = years[-1] - years[0] + 1 != n
    if gaps:
        w.append("temporal_gaps")
    if max(vals) == min(vals):
        w.append("degenerate_series")
        return TrendResult(region_id, variable, start_year, end_year, years[0], years[-1], n, "descriptive",
                           "ok", slope_dec, unit, total, None, None, None, None, None, None, None, None,
                           MOCK_METHOD_DESCRIPTIVE, coverage_fraction, tuple(w))
    if n < 30 or gaps:
        if n < 30:
            w.append("short_record")
        return TrendResult(region_id, variable, start_year, end_year, years[0], years[-1], n,
                           "descriptive", "ok", slope_dec, unit, total, None, None, None, None, None, None,
                           None, None, MOCK_METHOD_DESCRIPTIVE, coverage_fraction, tuple(w))
    factor = _PARAMS.get((region_id, variable), (0, 0, 0, 0.5))[3]
    se = round(max(abs(slope_dec) * factor, 1e-9), 6)
    p = _normal_two_sided_p(slope_dec / se)
    return TrendResult(region_id, variable, start_year, end_year, years[0], years[-1], n,
                       "inferential", "ok", slope_dec, unit, total,
                       round(slope_dec - 1.96 * se, 6), round(slope_dec + 1.96 * se, 6), se,
                       p, None, None, None, 3, MOCK_METHOD_INFERENTIAL, coverage_fraction,
                       tuple(w + ["mock_inference_placeholder"]))


def _raw_trend(variable, region_id, start_year, end_year):
    rows = [(r["year"], r["value"]) for r in get_annual_series(variable, region_id, start_year, end_year)]
    return fit_mock_trend(rows, region_id, variable, start_year, end_year)


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


_PENDING = "{} pendiente: el mock aun no lo implementa."

# Mock cell centres. Keep equal to src/regions.py VERIFIED_LAND_CELLS (checked by a test);
# not imported here so the mock stays stdlib-only.
_MOCK_CELLS = {
    "CR_PN": ((10.0, -85.625), (10.5, -85.625), (10.5, -85.0), (11.0, -85.625), (11.0, -85.0)),
    "CR_CAR": ((9.5, -83.75), (9.5, -83.125), (10.0, -83.75), (10.0, -83.125), (10.5, -83.75)),
}


def _cell_rows(variable, region_id, idx, start_year, end_year):
    # deterministic per-cell tilt on top of the regional synthetic series
    tilt = 0.15 * (idx - 2) * abs(_PARAMS[(region_id, variable)][1])
    return [(y, _synthetic_value(region_id, variable, y) + tilt * (y - COVERAGE_START_YEAR))
            for y in range(start_year, end_year + 1)]


def cell_family_id(variable: str, start_year: int, end_year: int) -> str:
    return f"cells|{variable}|CR_PN+CR_CAR|{start_year}-{end_year}|v2"


def get_cell_trends(variable: str, region_id: str, start_year: int, end_year: int) -> tuple:
    """(list[CellTrends] for region_id, family metadata dict). BY family = cells of BOTH sectors."""
    validate_query(variable, region_id, start_year, end_year)
    unit = SLOPE_UNITS[variable]
    raw = []  # (region, lat, lon, TrendResult)
    for rid in REGION_IDS:
        for i, (lat, lon) in enumerate(_MOCK_CELLS[rid]):
            t = fit_mock_trend(_cell_rows(variable, rid, i, start_year, end_year), rid, variable,
                               start_year, end_year)
            if t.p_value is not None:  # cell se widens with idx so q varies; still a placeholder
                se = max(t.se_hac * (1.0 + 0.4 * i), 1e-9)
                t = TrendResult(**{**t.__dict__, "se_hac": se,
                                   "p_value": _normal_two_sided_p(t.slope_per_decade / se)})
            raw.append((rid, lat, lon, t))
    valid = [i for i, r in enumerate(raw) if r[3].p_value is not None]
    q = dict(zip(valid, _by_adjust([raw[i][3].p_value for i in valid])))
    out = []
    for i, (rid, lat, lon, t) in enumerate(raw):
        if rid != region_id:
            continue
        qv = q.get(i)
        out.append(CellTrends(rid, variable, lat, lon, start_year, end_year, t.slope_per_decade, unit,
                              t.p_value, qv, None if qv is None else qv < FAMILY_ALPHA, t.n_years,
                              t.level, t.status))
    meta = FamilyMetadata(cell_family_id(variable, start_year, end_year), len(raw), len(valid),
                          FAMILY_ALPHA, "fdr_by", "cells", REGION_IDS, (variable,), start_year, end_year)
    return out, to_jsonable(meta)


def get_event_view(variable):
    raise NotImplementedError(_PENDING.format("get_event_view (P1)"))


def _check_query(query: QueryParams) -> None:
    validate_query(query.variable, None, query.start_year, query.end_year)
    for r in query.regions:
        validate_query(query.variable, r, query.start_year, query.end_year)
    if query.preset_id not in PRESET_IDS:
        raise ValueError(f"preset_id invalido: {query.preset_id!r}. Validos: {', '.join(PRESET_IDS)}.")


def _data_sha256(query: QueryParams) -> str:
    rows = [get_annual_series(query.variable, r, query.start_year, query.end_year) for r in query.regions]
    return sha256_hex(canonical_json(rows))


def _query_dict(query: QueryParams) -> dict:
    return {**query.__dict__, "regions": list(query.regions)}


def build_provenance(query: QueryParams) -> dict:
    _check_query(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "MOCK (sintetico, no NASA)",
        "source_page": None,
        "request_urls": [],
        "retrieved_at": None,
        "provider_version": None,
        "api_version": None,
        "native_resolution_deg": [0.5, 0.625],
        "raw_files": [],
        "transformations": ["generador sintetico determinista", "anualizacion simulada"],
        "mask_version": MASK_VERSION,
        "synthetic": SYNTHETIC,
        "query": _query_dict(query),
        "git_commit": None,
        "data_sha256": _data_sha256(query),
        "aggregation": "mock: sin agregacion real",
        "hac": {k: STATS_CONFIG[k] for k in ("hac_lags", "hac_sensitivity", "kernel", "use_t", "use_correction")},
        "correction_families": [family_id(query.start_year, query.end_year)],
        "limitations": ["Datos sinteticos de contrato; no son evidencia cientifica.",
                        "se/p/IC en nivel inferential son marcadores, no HAC real."],
    }


def _summary(results: list) -> str:
    parts = []
    for r in results:
        if r["slope_per_decade"] is None:
            parts.append(f"{r['region_id']}: sin pendiente calculable ({r['status']}).")
        elif r["level"] == "inferential":
            parts.append(f"{r['region_id']}: pendiente {r['slope_per_decade']:.3f} {r['slope_unit']}; "
                         "significancia evaluada con la familia ajustada (valores de ejemplo).")
        else:
            parts.append(f"{r['region_id']}: pendiente descriptiva {r['slope_per_decade']:.3f} "
                         f"{r['slope_unit']}; no se evalua significancia por duracion insuficiente.")
    return " ".join(parts)


def build_evidence_card(query: QueryParams, hypothesis: str = "") -> dict:
    """Evidence card v2 (plan 4.7). Same TrendResults as get_comparison; hypothesis never alters them."""
    _check_query(query)
    comp = get_comparison(query.variable, query.start_year, query.end_year, query.regions)
    data_sha = _data_sha256(query)
    qd = _query_dict(query)
    warnings = sorted({w for r in comp["results"] for w in r["warnings"]} | {"coarse_resolution"})
    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": compute_result_id(qd, data_sha, MASK_VERSION),
        "preset_id": query.preset_id,
        "hypothesis": hypothesis,
        "query": qd,
        "synthetic": SYNTHETIC,
        "summary": _summary(comp["results"]),
        "results": comp["results"],
        "family_metadata": comp["family_metadata"],
        "warnings": warnings,
        "source_ids": ["S1", "S2"],
        "data_sha256": data_sha,
        "mask_version": MASK_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
