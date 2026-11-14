"""Preparacion de series mensuales y anuales regionales (Hefesto v2, EMANUEL-03).

Propietario: Emanuel. Pure stdlib: ninguna dependencia externa (no hay pandas/numpy
en este entorno todavia; coincide con la convencion de `src/contracts.py` y
`src/service_mock.py` de usar `list[dict]` en vez de DataFrame).

Entrada esperada (misma forma de columnas que produce `src/ingest.py` +
`src/regions.py` en la rama `feat/data-cr-v2` de Samuel, aqui como listas de
dicts en vez de DataFrame de pandas):

  cell_rows: cada dict con region_id, variable, lat, lon, year, month,
             value (float o None si falta), unit, synthetic.
             (Equivale a una fila de `grid_monthly.parquet` con `time`
             descompuesto en year/month; ver `src/ingest.py::parse_payload_to_rows`.)
  mask_rows: cada dict con region_id, lat, lon, weight, mask_version.
             (Equivale a `masks.parquet`; ver `src/regions.py::build_masks_df`,
             pesos cos(lat) normalizados por region.)

Convencion de faltantes: `value is None` (nunca NaN/sentinela). `0.0` es un
valor valido, nunca se interpreta como faltante. Si la entrada real viene en
formato DataFrame de Samuel (columna `time` en vez de year/month, `value`
NaN en vez de `None`), pasarla primero por `adapt_cell_rows()`.

Politica de cobertura incompleta (PROVISIONAL, ver docs/emanuel/decisions.md
fila "Cobertura y año completo"): una region-mes solo produce un valor si
TODAS las celdas de la mascara de esa region tienen valor ese mes (cobertura
ponderada == 1.0, `COVERAGE_THRESHOLD`). Pendiente de confirmar con Jacky y
Samuel el umbral real sobre datos no sinteticos (ver seccion "Pendiente de
confirmar con Jacky" al final de este modulo).
"""
from __future__ import annotations

import calendar
import math
from typing import Any

from src.contracts import (
    ANNUAL_UNITS,
    COVERAGE_END_YEAR,
    COVERAGE_START_YEAR,
    MONTHLY_UNITS,
    REGION_IDS,
    VARIABLE_IDS,
)

# --------------------------------------------------------------------------- #
# Politica de cobertura - PROVISIONAL, ver docstring del modulo.
# --------------------------------------------------------------------------- #
COVERAGE_THRESHOLD = 1.0

# Faltante conocido de limpieza previa (ver src/ingest.py): si llega hasta aqui
# es que la ingesta no filtro el fill_value. Se trata como dato sospechoso, no
# se adivina su valor.
_SENTINEL_FILL_VALUE = -999.0


# --------------------------------------------------------------------------- #
# Calendario real (dias reales por mes/anio, incluye bisiestos). Se usa la
# libreria estandar `calendar`, nunca una formula propia: evita reinventar la
# regla de bisiestos y permite comprobarla contra Python directamente.
# --------------------------------------------------------------------------- #
def is_leap(year: int) -> bool:
    return calendar.isleap(year)


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def days_in_year(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def verify_leap_year_arithmetic() -> None:
    """Autocomprobacion de bisiestos contra casos conocidos (stdlib `calendar`).

    No es una prueba de negocio: es una guarda de que `calendar` se usa bien
    (regla 4/100/400) antes de agregar precipitacion acumulada por anio.
    """
    known = {1999: 365, 2000: 366, 1900: 365, 2001: 365, 2004: 366, 2024: 366}
    for year, expected in known.items():
        got = days_in_year(year)
        if got != expected:
            raise AssertionError(f"Aritmetica de bisiesto incorrecta para {year}: {got} != {expected}")


# --------------------------------------------------------------------------- #
# Adaptador de entrada (EMANUEL-03): columnas de Samuel -> columnas de este
# modulo. `src/ingest.py` (rama `feat/data-cr-v2` de Samuel) entrega filas de
# `grid_monthly.parquet` con columna `time` (fecha, no year/month) y, por ser
# DataFrame, valores faltantes como NaN (ver convencion de `src/contracts.py`:
# "DataFrame missing = NaN; JSON missing = null"), no como `None`. Este
# adaptador no cambia la logica de agregacion de abajo: solo normaliza la
# entrada antes de que llegue a `check_duplicates`/`build_regional_monthly`.
# --------------------------------------------------------------------------- #
def _time_to_year_month(time_value: Any) -> tuple[int, int]:
    """Convierte el campo `time` de Samuel a (year, month).

    Acepta cualquier objeto tipo fecha con atributos `.year`/`.month`
    (`datetime.date`, `datetime.datetime`, `pandas.Timestamp`) o una cadena
    ISO 8601 ("YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS", "YYYY-MM").
    """
    if hasattr(time_value, "year") and hasattr(time_value, "month"):
        return int(time_value.year), int(time_value.month)
    if isinstance(time_value, str):
        parts = time_value.strip().split("-")
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass
        raise ValueError(f"No se pudo interpretar `time` como fecha ISO: {time_value!r}")
    raise TypeError(f"Tipo de `time` no soportado: {type(time_value)!r} ({time_value!r})")


def _is_missing_value(value: Any) -> bool:
    """`None` o NaN cuentan como faltante; `0.0` (o cualquier otro numero) no."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def adapt_cell_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapta filas con columna `time` (formato Samuel) a la forma year/month.

    No modifica `raw_rows`: cada fila de entrada se copia a un dict nuevo.
    `value` NaN se traduce a `None` (convencion de este modulo); `0.0` se
    conserva intacto porque es un valor valido, nunca un faltante.
    """
    adapted: list[dict[str, Any]] = []
    for row in raw_rows:
        year, month = _time_to_year_month(row["time"])
        new_row = {key: value for key, value in row.items() if key != "time"}
        new_row["year"] = year
        new_row["month"] = month
        if _is_missing_value(new_row.get("value")):
            new_row["value"] = None
        adapted.append(new_row)
    return adapted


# --------------------------------------------------------------------------- #
# Validacion / QC de entrada
# --------------------------------------------------------------------------- #
def check_duplicates(cell_rows: list[dict[str, Any]]) -> None:
    """Lanza ValueError si hay filas con la misma llave primaria de celda-mes."""
    seen: set[tuple] = set()
    dups: list[tuple] = []
    for r in cell_rows:
        key = (r["region_id"], r["variable"], r["lat"], r["lon"], r["year"], r["month"])
        if key in seen:
            dups.append(key)
        else:
            seen.add(key)
    if dups:
        preview = dups[:5]
        suffix = "..." if len(dups) > 5 else ""
        raise ValueError(f"cell_rows tiene {len(dups)} llaves duplicadas: {preview}{suffix}")


def check_no_sentinel_values(cell_rows: list[dict[str, Any]]) -> None:
    """Lanza ValueError si queda un fill_value sin limpiar (ingesta incompleta).

    Un cero (0.0) es valido y nunca activa esto; solo valores <= -900 (ver
    `src/ingest.py`: fill_value NASA POWER es -999.0) delatan limpieza previa
    incompleta.
    """
    bad = [r for r in cell_rows if r["value"] is not None and r["value"] <= -900.0]
    if bad:
        raise ValueError(
            f"{len(bad)} filas con value <= -900 (sentinela NASA POWER sin limpiar), "
            f"ej. {bad[0]}"
        )


def check_region_variable_domains(cell_rows: list[dict[str, Any]]) -> None:
    bad_regions = {r["region_id"] for r in cell_rows} - set(REGION_IDS)
    bad_vars = {r["variable"] for r in cell_rows} - set(VARIABLE_IDS)
    if bad_regions:
        raise ValueError(f"region_id fuera de contrato: {sorted(bad_regions)}")
    if bad_vars:
        raise ValueError(f"variable fuera de contrato: {sorted(bad_vars)}")


def check_mask_weights(mask_rows: list[dict[str, Any]], *, atol: float = 1e-6) -> None:
    """Replica la garantia de `scripts/build_data.py::run_qc` (pesos suman 1 por region).

    Antes de sumar, exige que cada peso individual sea finito (no NaN/Inf) y
    no negativo: un peso invalido (p.ej. NaN de `cos(lat)` mal calculado)
    contamina la suma de su region y produce un error de "no suma 1.0" que
    oculta la causa real.
    """
    for m in mask_rows:
        weight = m["weight"]
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(
                f"Peso invalido en mascara de {m['region_id']!r} "
                f"(lat={m['lat']}, lon={m['lon']}): {weight!r} (debe ser finito y >= 0)"
            )
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for m in mask_rows:
        totals[m["region_id"]] = totals.get(m["region_id"], 0.0) + m["weight"]
        counts[m["region_id"]] = counts.get(m["region_id"], 0) + 1
    for region_id in REGION_IDS:
        total = totals.get(region_id)
        if total is None:
            raise ValueError(f"Mascara sin celdas para {region_id!r}")
        if abs(total - 1.0) > atol:
            raise ValueError(f"Pesos de {region_id} suman {total}, no 1.0")
        if counts[region_id] < 2:
            raise ValueError(f"{region_id} tiene menos de 2 celdas en la mascara")


def find_missing_cell_months(
    cell_rows: list[dict[str, Any]],
    mask_rows: list[dict[str, Any]],
    *,
    variables: tuple[str, ...] = VARIABLE_IDS,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
) -> dict[tuple[str, str, float, float], list[tuple[int, int]]]:
    """Mapa celda->lista de (year, month) sin fila o con value None.

    No filas y filas con value=None se tratan igual: ambas son "sin dato" para
    esta celda ese mes. Informativo: datos reales pueden tener huecos legitimos
    (no es un error fatal por si solo, a diferencia de un duplicado).
    """
    present: dict[tuple, float | None] = {
        (r["region_id"], r["variable"], r["lat"], r["lon"], r["year"], r["month"]): r["value"]
        for r in cell_rows
    }
    missing: dict[tuple[str, str, float, float], list[tuple[int, int]]] = {}
    for m in mask_rows:
        region_id, lat, lon = m["region_id"], m["lat"], m["lon"]
        for variable in variables:
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    key = (region_id, variable, lat, lon, year, month)
                    if present.get(key) is None:
                        missing.setdefault((region_id, variable, lat, lon), []).append((year, month))
    return missing


def run_qc(
    cell_rows: list[dict[str, Any]],
    mask_rows: list[dict[str, Any]],
    *,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
) -> dict[str, Any]:
    """Orquesta las comprobaciones obligatorias de EMANUEL-03.

    Lanza ValueError ante duplicados, sentinelas sin limpiar, dominios invalidos
    o mascara mal normalizada (errores de datos, no deberian ocurrir con una
    ingesta correcta). Los meses ausentes se reportan pero no son fatales: un
    hueco real en NASA POWER es un dato legitimo, no un bug.
    """
    verify_leap_year_arithmetic()
    check_duplicates(cell_rows)
    check_no_sentinel_values(cell_rows)
    check_region_variable_domains(cell_rows)
    check_mask_weights(mask_rows)
    missing = find_missing_cell_months(cell_rows, mask_rows, start_year=start_year, end_year=end_year)
    zero_count = sum(1 for r in cell_rows if r["value"] == 0.0)
    return {
        "leap_year_arithmetic_ok": True,
        "duplicates_ok": True,
        "sentinel_values_ok": True,
        "mask_weights_ok": True,
        "zero_value_count": zero_count,
        "missing_cell_months": {k: len(v) for k, v in missing.items()},
        "cells_with_any_gap": len(missing),
    }


# --------------------------------------------------------------------------- #
# Cobertura ponderada (misma formula que tests/fixtures/stats/regional_coverage.json)
# --------------------------------------------------------------------------- #
def weighted_mean(
    values: list[float | None], weights: list[float], *, threshold: float = COVERAGE_THRESHOLD
) -> tuple[float | None, float]:
    """Media ponderada con cobertura; ausente si la cobertura cae bajo `threshold`.

    Replica exactamente la referencia de Emanuel en
    `tests/fixtures/stats/generate_and_verify.py::weighted_mean`.
    """
    total_weight = sum(weights)
    if total_weight <= 0:
        return None, 0.0
    valid_weight = sum(w for w, v in zip(weights, values) if v is not None)
    coverage = valid_weight / total_weight
    if coverage < threshold or valid_weight <= 0:
        return None, coverage
    num = sum(w * v for w, v in zip(weights, values) if v is not None)
    return num / valid_weight, coverage


# --------------------------------------------------------------------------- #
# RegionalMonthly
# --------------------------------------------------------------------------- #
def build_regional_monthly(
    cell_rows: list[dict[str, Any]],
    mask_rows: list[dict[str, Any]],
    *,
    regions: tuple[str, ...] = REGION_IDS,
    variables: tuple[str, ...] = VARIABLE_IDS,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
    coverage_threshold: float = COVERAGE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Agrega celdas a promedio regional ponderado por mes.

    Cada fila de salida: region_id, variable, year, month, value (None si la
    cobertura ponderada < `coverage_threshold`), unit, coverage_fraction,
    n_cells_valid, n_cells_total.
    """
    check_duplicates(cell_rows)

    cells_by_region: dict[str, list[tuple[float, float, float]]] = {}
    for m in mask_rows:
        cells_by_region.setdefault(m["region_id"], []).append((m["lat"], m["lon"], m["weight"]))

    value_index: dict[tuple, float | None] = {
        (r["region_id"], r["variable"], r["lat"], r["lon"], r["year"], r["month"]): r["value"]
        for r in cell_rows
    }

    out: list[dict[str, Any]] = []
    for region_id in regions:
        cells = cells_by_region.get(region_id, [])
        for variable in variables:
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    values = [value_index.get((region_id, variable, lat, lon, year, month)) for lat, lon, _ in cells]
                    weights = [w for _, _, w in cells]
                    mean, coverage = weighted_mean(values, weights, threshold=coverage_threshold)
                    out.append(
                        {
                            "region_id": region_id,
                            "variable": variable,
                            "year": year,
                            "month": month,
                            "value": mean,
                            "unit": MONTHLY_UNITS[variable],
                            "coverage_fraction": coverage,
                            "n_cells_valid": sum(1 for v in values if v is not None),
                            "n_cells_total": len(cells),
                        }
                    )
    return out


# --------------------------------------------------------------------------- #
# RegionalAnnual
# --------------------------------------------------------------------------- #
def build_regional_annual(
    regional_monthly_rows: list[dict[str, Any]],
    *,
    regions: tuple[str, ...] = REGION_IDS,
    variables: tuple[str, ...] = VARIABLE_IDS,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
) -> list[dict[str, Any]]:
    """Resume RegionalMonthly a anual: 12 meses validos y dias reales (bisiesto incluido).

    T2M: media anual ponderada por dias de cada mes (sum(d_m * v_m) / dias_anio).
    PRECTOTCORR: acumulado anual (sum(d_m * v_m), tasa mm/day * dias -> mm/yr).
    Si faltan meses validos (`months_valid < 12`), `value` es None y se agrega
    el warning `incomplete_year`: ver politica PROVISIONAL en el docstring del
    modulo, pendiente de confirmar con Jacky y Samuel.
    """
    monthly_index = {(r["region_id"], r["variable"], r["year"], r["month"]): r for r in regional_monthly_rows}

    out: list[dict[str, Any]] = []
    for region_id in regions:
        for variable in variables:
            if variable not in ANNUAL_UNITS:
                raise ValueError(f"Variable sin regla de agregacion anual: {variable!r}")
            for year in range(start_year, end_year + 1):
                months = [monthly_index.get((region_id, variable, year, m)) for m in range(1, 13)]
                valid = [(m, rec) for m, rec in zip(range(1, 13), months) if rec is not None and rec["value"] is not None]
                months_valid = len(valid)
                complete = months_valid == 12
                warnings: list[str] = []
                value: float | None = None
                if complete:
                    if variable == "T2M":
                        total_days = days_in_year(year)
                        weighted_sum = sum(days_in_month(year, m) * rec["value"] for m, rec in valid)
                        value = weighted_sum / total_days
                    elif variable == "PRECTOTCORR":
                        value = sum(days_in_month(year, m) * rec["value"] for m, rec in valid)
                else:
                    warnings.append("incomplete_year")

                have_all_months = all(rec is not None for rec in months)
                mean_monthly_coverage = (
                    sum(rec["coverage_fraction"] for rec in months) / 12 if have_all_months else None
                )

                out.append(
                    {
                        "region_id": region_id,
                        "variable": variable,
                        "year": year,
                        "value": value,
                        "unit": ANNUAL_UNITS[variable],
                        "months_valid": months_valid,
                        "complete": complete,
                        "mean_monthly_coverage": mean_monthly_coverage,
                        "warnings": tuple(warnings),
                    }
                )
    return out


# --------------------------------------------------------------------------- #
# Orquestacion
# --------------------------------------------------------------------------- #
def prepare_regional_series(
    cell_rows: list[dict[str, Any]],
    mask_rows: list[dict[str, Any]],
    *,
    start_year: int = COVERAGE_START_YEAR,
    end_year: int = COVERAGE_END_YEAR,
    coverage_threshold: float = COVERAGE_THRESHOLD,
) -> dict[str, Any]:
    """Punto de entrada EMANUEL-03: QC + RegionalMonthly + RegionalAnnual."""
    qc_report = run_qc(cell_rows, mask_rows, start_year=start_year, end_year=end_year)
    regional_monthly = build_regional_monthly(
        cell_rows,
        mask_rows,
        start_year=start_year,
        end_year=end_year,
        coverage_threshold=coverage_threshold,
    )
    regional_annual = build_regional_annual(regional_monthly, start_year=start_year, end_year=end_year)
    return {
        "qc_report": qc_report,
        "regional_monthly": regional_monthly,
        "regional_annual": regional_annual,
    }


# --------------------------------------------------------------------------- #
# Pendiente de confirmar con Jacky (ver tambien docs/emanuel/decisions.md):
#
# 1. Umbral de cobertura: hoy COVERAGE_THRESHOLD=1.0 exige el 100% del peso de
#    la mascara presente para publicar un valor regional-mes. Con datos reales
#    (huecos legitimos de NASA POWER) esto puede dejar demasiados meses/anios
#    sin valor. Falta decidir si se permite un umbral menor y como se expondria
#    en TrendResult.coverage_fraction.
# 2. Año incompleto -> valor anual ausente (en vez de promediar solo los meses
#    presentes). Coincide con la propuesta de la tabla EMANUEL-01, pero no esta
#    confirmado como regla final del contrato v2.
# 3. mean_monthly_coverage es un campo informativo nuevo (no esta en
#    contracts.py); falta decidir si viaja hasta TrendResult/RegionalAnnual
#    como contrato o se queda solo como diagnostico interno de prepare.py.
# 4. Unidad mensual de PRECTOTCORR (mm/day) y el bbox/malla de ingest.py siguen
#    con [verificar] segun docs/decisions.md Q1; este modulo asume que ya
#    llegan limpios (sin fill_value) desde src/ingest.py.
# --------------------------------------------------------------------------- #
