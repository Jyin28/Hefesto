"""Servicio REAL de AguaAlerta v2 (mismas firmas y formas de retorno que `service_mock`).

Punto de entrada único de la UI: NO calcula pendientes ni p en la UI; todo sale de
`prepare` → `statistics`/`evidence` sobre los datos NASA POWER del repositorio.
Los cálculos con familia BY se hacen completos (ambos sectores) antes de filtrar la vista.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .contracts import (
    ANALYSIS_VERSION, ANNUAL_UNITS, COVERAGE_END_YEAR, COVERAGE_START_YEAR, MONTHLY_UNITS, PRESET_IDS,
    REGION_IDS, SCHEMA_VERSION, SLOPE_UNITS, STATS_CONFIG, VARIABLE_IDS, CellTrends, FamilyMetadata,
    QueryParams, TrendResult, VariableInfo, canonical_json, compute_result_id, sha256_hex, to_jsonable,
    validate_query,
)
from .enso import DEFAULT_EVENT_ID, episode_comparison
from .regions import MASK_VERSION, REGION_SPECS
from .web_data import ROOT, _evidence, climate_package, read_json

SYNTHETIC = False
SOURCE_IDS = ["S1", "S2", "S3", "S4"]

_VARIABLES = (
    VariableInfo(
        id="T2M", label="Temperatura del aire a 2 m",
        definition="Temperatura media del aire a 2 metros; la anual es la media ponderada por días.",
        unit_monthly=MONTHLY_UNITS["T2M"], unit_annual=ANNUAL_UNITS["T2M"], source_id="S1",
        limitations=("Estimación de reanálisis con asimilación de observaciones, no un termómetro",
                     "Resolución nativa ~0,5° × 0,625° (decenas de km)"),
    ),
    VariableInfo(
        id="PRECTOTCORR", label="Precipitación corregida",
        definition="Tasa de precipitación corregida (mm/día); la anual es la suma de tasa mensual × días (mm/año).",
        unit_monthly=MONTHLY_UNITS["PRECTOTCORR"], unit_annual=ANNUAL_UNITS["PRECTOTCORR"], source_id="S1",
        limitations=("No mide caudal, humedad de suelo, recarga ni suministro de agua",
                     "Lluvia de reanálisis: sin validar contra estaciones; puede tener sesgos y cambios de fuente",
                     "Resolución nativa ~0,5° × 0,625° (decenas de km)"),
    ),
)

WARNING_TEXT = {
    "short_record": "Serie corta: no se evalúa significancia.",
    "short_for_inference": "Menos de 30 años consecutivos: solo magnitud descriptiva.",
    "temporal_gaps": "Hay años faltantes dentro de la ventana: pendiente descriptiva, sin inferencia.",
    "incomplete_years": "Algunos años de la ventana no están completos y no se usaron.",
    "degenerate_series": "Serie sin variación suficiente: no se puede estimar p ni intervalo.",
    "coverage_failure": "Cobertura espacial menor al 80 %: dato insuficiente.",
    "no_data": "Sin datos en la ventana.",
    "possible_inhomogeneity": "Se detectó un salto de nivel en la serie (posible cambio de fuente o de régimen).",
    "reanalysis_precip_caution": (
        "La lluvia de reanálisis no está validada con estaciones; NASA POWER documenta que los datos recientes "
        "pueden provenir de GEOS-IT sin normalización por pluviómetros. Úsela como patrón del producto, "
        "no como lluvia observada."
    ),
    "coarse_resolution": "Celdas de decenas de km: no representan fincas, cantones ni cuencas.",
}


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
def list_variables() -> list[VariableInfo]:
    return list(_VARIABLES)


def list_regions():
    return list(REGION_SPECS.values())


def get_coverage() -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "synthetic": SYNTHETIC, "start_year": COVERAGE_START_YEAR,
        "end_year": COVERAGE_END_YEAR, "regions": list(REGION_IDS), "variables": list(VARIABLE_IDS),
        "mask_version": MASK_VERSION,
    }


# --------------------------------------------------------------------------- #
# Series y tendencias
# --------------------------------------------------------------------------- #
def _annual_rows():
    return climate_package()[0]["regional_annual"]


def get_annual_series(variable, region_id, start_year, end_year):
    validate_query(variable, region_id, start_year, end_year)
    return [
        {"region_id": r["region_id"], "variable": r["variable"], "year": r["year"], "value": r["value"],
         "unit": r["unit"], "months_valid": r["months_valid"], "complete": r["complete"], "synthetic": SYNTHETIC}
        for r in _annual_rows()
        if r["region_id"] == region_id and r["variable"] == variable and start_year <= r["year"] <= end_year
    ]


def _regional_family(start_year, end_year):
    entries, families = _evidence(start_year, end_year)
    return entries, families["ols"]


def get_trend(variable, region_id, start_year, end_year) -> TrendResult:
    validate_query(variable, region_id, start_year, end_year)
    entries, _ = _regional_family(start_year, end_year)  # familia completa (4 pruebas), no el subconjunto
    return entries[region_id, variable]["ols"]


def get_comparison(variable, start_year, end_year, regions=REGION_IDS) -> dict:
    validate_query(variable, None, start_year, end_year)
    for region in regions:
        validate_query(variable, region, start_year, end_year)
    entries, meta = _regional_family(start_year, end_year)
    return {
        "schema_version": SCHEMA_VERSION, "synthetic": SYNTHETIC, "variable": variable,
        "start_year": start_year, "end_year": end_year,
        "results": [to_jsonable(entries[region, variable]["ols"]) for region in regions],
        "family_metadata": [to_jsonable(_family_meta(meta))],
    }


def _family_meta(meta: dict) -> FamilyMetadata:
    return FamilyMetadata(
        family_id=meta["family_id"], planned_tests=meta["planned_tests"], valid_tests=meta["valid_tests"],
        alpha=meta["alpha"], method=meta["method"], scope=meta["scope"], regions=tuple(meta["regions"]),
        variables=tuple(meta["variables"]), start_year=meta["start_year"], end_year=meta["end_year"],
    )


def get_cell_trends(variable, region_id, start_year, end_year):
    """(list[CellTrends] del sector, metadatos de la familia). BY sobre las celdas de AMBOS sectores."""
    validate_query(variable, region_id, start_year, end_year)
    entries, families = _evidence(start_year, end_year, variable)
    cells = climate_package()[1]
    out = []
    for cell_id, cell in cells.items():
        if region_id not in cell["regions"]:
            continue
        t = entries[cell_id, variable]["ols"]
        out.append(CellTrends(
            region_id=region_id, variable=variable, lat=cell["lat"], lon=cell["lon"],
            start_year=start_year, end_year=end_year, slope_per_decade=t.slope_per_decade,
            slope_unit=SLOPE_UNITS[variable], p_value=t.p_value, q_value=t.p_adjusted,
            significant=t.significant, n_years=t.n_years, level=t.level, status=t.status,
        ))
    return out, to_jsonable(_family_meta(families["ols"]))


def get_diagnostics(variable, region_id, start_year, end_year) -> dict:
    """Sensibilidad HAC (L=1/5), homogeneidad y Mann–Kendall como contraste (no sustituyen al OLS+HAC)."""
    validate_query(variable, region_id, start_year, end_year)
    entry = _regional_family(start_year, end_year)[0][region_id, variable]
    return to_jsonable({
        "hac_main_lags": STATS_CONFIG["hac_lags"],
        "hac_sensitivity": entry["hac_sensitivity"],
        "hac_sensitivity_changes_conclusion": entry["hac_sensitivity_changes_conclusion"],
        "homogeneity": entry["homogeneity"],
        "mann_kendall": entry["mann_kendall"],
    })


# --------------------------------------------------------------------------- #
# Episodio ENOS (P1, descriptivo)
# --------------------------------------------------------------------------- #
def get_event_view(variable, event_id=DEFAULT_EVENT_ID) -> list:
    """Filas mensuales {region_id, time, value, climatology, anomaly, unit, baseline, label}."""
    validate_query(variable, None, COVERAGE_START_YEAR, COVERAGE_END_YEAR)
    monthly = climate_package()[0]["regional_monthly"]
    catalog = read_json(ROOT / "data" / "web" / "enso.json")
    rows = []
    for region in REGION_IDS:
        event = episode_comparison([r for r in monthly if r["region_id"] == region], variable, catalog,
                                   COVERAGE_START_YEAR, COVERAGE_END_YEAR, event_id=event_id)
        for m in event["months"]:
            rows.append({
                "region_id": region, "time": m["date"] + "-01", "value": m["value"],
                "climatology": m["normal"], "anomaly": m["anomaly"], "unit": event["unit"],
                "baseline": "1981-2010", "label": event["label"], "event_id": event_id,
                "neutral_status": event["status"],
            })
    return rows


# --------------------------------------------------------------------------- #
# Procedencia y ficha
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(ROOT), capture_output=True, text=True,
                             timeout=5, check=False)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _check_query(query: QueryParams) -> None:
    validate_query(query.variable, None, query.start_year, query.end_year)
    for region in query.regions:
        validate_query(query.variable, region, query.start_year, query.end_year)
    if query.preset_id not in PRESET_IDS:
        raise ValueError(f"preset_id inválido: {query.preset_id!r}. Válidos: {', '.join(PRESET_IDS)}.")


def _query_dict(query: QueryParams) -> dict:
    return {**query.__dict__, "regions": list(query.regions)}


def _data_sha256(query: QueryParams) -> str:
    base = climate_package()[2]
    rows = [get_annual_series(query.variable, r, query.start_year, query.end_year) for r in query.regions]
    return sha256_hex(canonical_json({"raw": base["raw_files"], "annual": rows}))


def build_provenance(query: QueryParams) -> dict:
    _check_query(query)
    base = climate_package()[2]
    families = [_regional_family(query.start_year, query.end_year)[1]["family_id"],
                _evidence(query.start_year, query.end_year, query.variable)[1]["ols"]["family_id"]]
    return to_jsonable({
        **base, "schema_version": SCHEMA_VERSION, "query": _query_dict(query), "git_commit": _git_commit(),
        "data_sha256": _data_sha256(query), "synthetic": SYNTHETIC,
        "aggregation": ("Máscara fija de celdas terrestres (pesos cos(lat)); ≥80 % del peso elegible; "
                        "T2M anual = media ponderada por días, PRECTOTCORR anual = Σ tasa × días (mm/año); "
                        "año con 12 meses válidos."),
        "hac": {k: STATS_CONFIG[k] for k in ("hac_lags", "hac_sensitivity", "kernel", "use_t", "use_correction")},
        "correction_families": families,
        "limitations": _limitations(query),
    })


def _limitations(query: QueryParams) -> list:
    out = [REGION_SPECS[r].scale_warning for r in query.regions]
    out += [
        "Reanálisis de modelo con asimilación de observaciones; no es medición directa.",
        "Exploración histórica: no pronostica sequías, inundaciones ni disponibilidad de agua potable.",
        "No significativo significa evidencia insuficiente, no 'no cambia'. Asociación no es causa.",
        "IC del 95 % individual, no simultáneo. FDR (BY) no corrige todas las búsquedas hechas en la sesión.",
    ]
    if query.variable == "PRECTOTCORR":
        out.append(WARNING_TEXT["reanalysis_precip_caution"])
    return out


def fmt_p(p) -> str:
    if p is None:
        return "N/D"
    return "<0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ",")


def _fmt(x, nd=3) -> str:
    return "N/D" if x is None else f"{x:.{nd}f}".replace(".", ",")


def _sector(region_id) -> str:
    return "Pacífico Norte" if region_id == "CR_PN" else "Caribe"


def _summary(results: list) -> str:
    parts = []
    for r in results:
        name = _sector(r["region_id"])
        if r["slope_per_decade"] is None:
            parts.append(f"{name}: sin pendiente calculable ({r['status']}).")
        elif r["level"] == "inferential":
            verdict = ("hay evidencia estadística de cambio lineal (p ajustado BY < 0,05)" if r["significant"]
                       else "evidencia insuficiente para afirmar un cambio lineal (p ajustado BY ≥ 0,05)")
            parts.append(
                f"{name}: pendiente {_fmt(r['slope_per_decade'])} {r['slope_unit']} "
                f"(IC 95 % individual [{_fmt(r['ci_low'])}, {_fmt(r['ci_high'])}]); p = {fmt_p(r['p_value'])}, "
                f"p ajustado = {fmt_p(r['p_adjusted'])}: {verdict}."
            )
        else:
            parts.append(
                f"{name}: pendiente descriptiva {_fmt(r['slope_per_decade'])} {r['slope_unit']}; "
                "no se evalúa significancia (menos de 30 años consecutivos o huecos)."
            )
    return " ".join(parts)


def build_evidence_card(query: QueryParams, hypothesis: str = "") -> dict:
    """Ficha de detective v2 (plan §4.7). La hipótesis nunca altera el análisis."""
    _check_query(query)
    comp = get_comparison(query.variable, query.start_year, query.end_year, query.regions)
    meta = comp["family_metadata"]
    cell_meta = [get_cell_trends(query.variable, query.regions[0], query.start_year, query.end_year)[1]]
    data_sha = _data_sha256(query)
    qd = _query_dict(query)
    warnings = sorted({w for r in comp["results"] for w in r["warnings"]} | {"coarse_resolution"})
    summary = _summary(comp["results"])
    if query.variable == "PRECTOTCORR":
        summary += " Precaución: " + WARNING_TEXT["reanalysis_precip_caution"]
    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": compute_result_id(qd, data_sha, MASK_VERSION),
        "preset_id": query.preset_id, "hypothesis": hypothesis, "query": qd, "synthetic": SYNTHETIC,
        "summary": summary, "results": comp["results"],
        "family_metadata": meta + cell_meta, "warnings": warnings, "source_ids": SOURCE_IDS,
        "data_sha256": data_sha, "mask_version": MASK_VERSION, "analysis_version": ANALYSIS_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": [row for r in query.regions
                   for row in get_annual_series(query.variable, r, query.start_year, query.end_year)],
        "diagnostics": {r: get_diagnostics(query.variable, r, query.start_year, query.end_year)
                        for r in query.regions},
        "provenance": build_provenance(query),
    }


# --------------------------------------------------------------------------- #
# Vista mensual (visualización/aprendizaje; NO es evidencia de tendencia)
# --------------------------------------------------------------------------- #
MIN_BASELINE_YEARS = 24  # plan §3.3


def get_monthly_view(variable, region_id, start_year, end_year) -> list:
    """Filas {region_id, time, year, month, value, climatology, anomaly, unit}.

    climatology = media del mismo mes en 1981–2010 (exige ≥24 valores de los 30 años, si no, None).
    """
    validate_query(variable, region_id, start_year, end_year)
    monthly = [r for r in climate_package()[0]["regional_monthly"]
               if r["region_id"] == region_id and r["variable"] == variable]
    clim = {}
    for month in range(1, 13):
        sample = [r["value"] for r in monthly if r["month"] == month and 1981 <= r["year"] <= 2010
                  and r["value"] is not None]
        clim[month] = sum(sample) / len(sample) if len(sample) >= MIN_BASELINE_YEARS else None
    rows = []
    for r in monthly:
        if not start_year <= r["year"] <= end_year:
            continue
        c = clim[r["month"]]
        rows.append({
            "region_id": region_id, "time": f"{r['year']}-{r['month']:02d}-01", "year": r["year"],
            "month": r["month"], "value": r["value"], "climatology": c, "unit": r["unit"],
            "anomaly": (r["value"] - c) if r["value"] is not None and c is not None else None,
        })
    return rows
