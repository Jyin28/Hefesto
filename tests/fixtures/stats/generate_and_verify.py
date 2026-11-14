"""Genera y verifica los fixtures sinteticos de EMANUEL-02.

Estos fixtures son referencias numericas sinteticas. Las regiones y unidades
siguen el contrato v2. Los campos de cada caso describen sus entradas y
resultados de prueba. Cada fixture declara synthetic=True, unit y status.

Ejecucion: python tests/fixtures/stats/generate_and_verify.py
Regenera los .json en este directorio y corre las comprobaciones contra los
valores de referencia de los casos de EMANUEL-02.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    days = [31, 29 if is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return days[month - 1]


def days_in_year(year: int) -> int:
    return 366 if is_leap(year) else 365


def ols_centered_sums(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Pendiente e intercepto por sumas centradas (formula 1)."""
    n = len(xs)
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    sxx = sum((x - xbar) ** 2 for x in xs)
    b = sxy / sxx
    a = ybar - b * xbar
    return b, a


def ols_cross_check(xs: list[float], ys: list[float]) -> float:
    """Pendiente por la formula de sumas brutas (formula 2, independiente de la 1)."""
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def weighted_mean(values: list[float | None], weights: list[float]) -> tuple[float | None, float]:
    total_weight = sum(weights)
    valid_weight = sum(w for w, v in zip(weights, values) if v is not None)
    coverage = valid_weight / total_weight
    if coverage < 1.0:
        return None, coverage
    num = sum(w * v for w, v in zip(weights, values) if v is not None)
    return num / valid_weight, coverage


def fdr_by(pvals: list[float]) -> list[float]:
    """Benjamini-Yekutieli, devuelto en el orden original de entrada."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    ranked = [pvals[i] for i in order]
    h_m = sum(1.0 / k for k in range(1, m + 1))
    raw = [min(1.0, m * h_m * ranked[j] / (j + 1)) for j in range(m)]
    q_sorted = [0.0] * m
    q_sorted[-1] = raw[-1]
    for j in range(m - 2, -1, -1):
        q_sorted[j] = min(raw[j], q_sorted[j + 1])
    q = [0.0] * m
    for rank_pos, orig_i in enumerate(order):
        q[orig_i] = q_sorted[rank_pos]
    return q


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


CHECKS: list[str] = []


def check(label: str, got, expected, tol: float = 1e-6) -> None:
    ok = approx(got, expected, tol) if isinstance(expected, (int, float)) else got == expected
    status = "OK" if ok else "FALLA"
    CHECKS.append(f"[{status}] {label}: obtenido={got!r} esperado={expected!r}")
    if not ok:
        raise AssertionError(f"{label}: obtenido={got!r} esperado={expected!r}")


def write_fixture(name: str, payload: dict) -> None:
    path = HERE / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Caso 1-2: rectas exactas (aumento / disminucion)
# ---------------------------------------------------------------------------
def build_linear_case(name: str, start_year: int, n_years: int, intercept: float, slope: float, unit: str):
    years = [start_year + t for t in range(n_years)]
    ts = [float(t) for t in range(n_years)]
    values = [intercept + slope * t for t in ts]
    b, a = ols_centered_sums(ts, values)
    b_cross = ols_cross_check(ts, values)
    decadal = 10 * b
    adjusted_change = b * (ts[-1] - ts[0])
    payload = {
        "case_id": name,
        "synthetic": True,
        "status": "descriptivo_ajuste_exacto",
        "status_note": (
            "Recta exacta sin ruido: covarianza degenerada, la magnitud es identificable "
            "pero p, q e IC quedan ausentes (propuesta EMANUEL-01, fila 'Inferencia')."
        ),
        "unit": unit,
        "unit_slope": f"{unit}/decade",
        "input": {
            "variable": "T2M",
            "years": years,
            "annual_values": values,
        },
        "expected": {
            "slope_per_year": b,
            "slope_per_decade": decadal,
            "adjusted_change": adjusted_change,
            "first_year_used": years[0],
            "last_year_used": years[-1],
            "years_used": n_years,
            "inference": "ausente",
        },
        "independent_reference": {
            "method": "OLS por sumas centradas (formula 1) y sumas brutas (formula 2, cruce independiente)",
            "slope_cross_check": b_cross,
        },
    }
    write_fixture(name, payload)
    return payload


# ---------------------------------------------------------------------------
# Caso 3: estacionalidad sin tendencia
# ---------------------------------------------------------------------------
def build_seasonality_case():
    years = list(range(1990, 1995))  # incluye 1992, bisiesto
    month_values = {7: 20.0, 8: 10.0}
    default_value = 15.0
    annual_series = []
    monthly_detail_by_year = {}
    for year in years:
        monthly_values = [month_values.get(m, default_value) for m in range(1, 13)]
        days = [days_in_month(year, m) for m in range(1, 13)]
        total_days = days_in_year(year)
        weighted_sum = sum(d * v for d, v in zip(days, monthly_values))
        annual_mean = weighted_sum / total_days
        annual_series.append(annual_mean)
        monthly_detail_by_year[str(year)] = {
            "monthly_values": monthly_values,
            "days_in_month": days,
            "total_days": total_days,
            "annual_mean": annual_mean,
        }
    ts = [float(t) for t in range(len(years))]
    b, a = ols_centered_sums(ts, annual_series)
    anomalies = {
        "julio": month_values[7] - month_values[7],
        "agosto": month_values[8] - month_values[8],
        "otro_mes_generico": default_value - default_value,
    }
    payload = {
        "case_id": "seasonality_no_trend",
        "synthetic": True,
        "status": "descriptivo_ajuste_exacto",
        "status_note": "Ciclo estacional repetido cada ano: pendiente nula, sin tendencia real que inferir.",
        "unit": "degC",
        "unit_slope": "degC/decade",
        "input": {
            "variable": "T2M",
            "years": years,
            "month_values_pattern": {"julio": 20.0, "agosto": 10.0, "otros_meses": 15.0},
            "detail_by_year": monthly_detail_by_year,
        },
        "expected": {
            "annual_means": dict(zip((str(y) for y in years), annual_series)),
            "annual_mean_is_constant_15": all(approx(v, 15.0) for v in annual_series),
            "slope_per_year": b,
            "slope_per_decade": 10 * b,
            "anomalies_vs_same_climatology": anomalies,
            "inference": "ausente",
        },
        "independent_reference": {
            "method": (
                "Julio y agosto tienen 31 dias cada uno en todo anio (bisiesto o no); "
                "media anual = (31*20 + 31*10 + (total_dias-62)*15) / total_dias = 15 exacto, "
                "demostrado algebraicamente para total_dias en {365, 366}."
            )
        },
    }
    write_fixture("seasonality_no_trend", payload)
    return payload, annual_series


# ---------------------------------------------------------------------------
# Caso 4: AR(1) con semilla fija
# ---------------------------------------------------------------------------
def build_ar1_case():
    n_years = 30
    start_year = 1990
    rng = random.Random(42)
    innovations = [rng.gauss(0, 1) for _ in range(n_years)]
    e_prev = 0.0
    errors = []
    for innovation in innovations:
        e_t = 0.6 * e_prev + innovation
        errors.append(e_t)
        e_prev = e_t
    ts = [float(t) for t in range(n_years)]
    values = [20 + 0.02 * t + e for t, e in zip(ts, errors)]
    years = [start_year + t for t in range(n_years)]

    # Reproducibilidad: una segunda corrida independiente con la misma semilla
    rng2 = random.Random(42)
    innovations2 = [rng2.gauss(0, 1) for _ in range(n_years)]
    reproducible = innovations == innovations2

    b, a = ols_centered_sums(ts, values)
    b_cross = ols_cross_check(ts, values)

    payload = {
        "case_id": "ar1_seed42",
        "synthetic": True,
        "status": "ventana_30_anios_elegible_para_hac",
        "status_note": (
            "30 anios completos y consecutivos: ventana elegible para HAC segun la propuesta "
            "EMANUEL-01 ('Inferencia'). No se fija expectativa de significancia para una sola "
            "realizacion AR(1); eso se deja para EMANUEL-04/07 con HAC real."
        ),
        "unit": "degC",
        "unit_slope": "degC/decade",
        "input": {
            "variable": "T2M",
            "years": years,
            "model": "y_t = 20 + 0.02*t + e_t ; e_t = 0.6*e_{t-1} + innovacion_t ; e_{-1} = 0",
            "rng": "random.Random(42).gauss(0, 1), un valor por anio, en orden",
            "innovations": innovations,
            "errors": errors,
            "annual_values": values,
        },
        "expected": {
            "slope_per_year_ols_centered_sums": b,
            "slope_per_decade": 10 * b,
            "reproducible_with_seed_42": reproducible,
        },
        "independent_reference": {
            "method": "Cruce de la pendiente OLS con formula de sumas brutas, independiente de la de sumas centradas.",
            "slope_cross_check": b_cross,
            "note": (
                "El valor de b no depende del numero de rezagos HAC (L=1,3,5): L solo cambia la "
                "estimacion de la covarianza/SE, nunca el punto b. Por eso 'la pendiente coincide "
                "para L=1,3,5' es una propiedad de la formula OLS, no un resultado a simular aqui."
            ),
        },
    }
    write_fixture("ar1_seed42", payload)
    return payload


# ---------------------------------------------------------------------------
# Caso 5: anio incompleto
# ---------------------------------------------------------------------------
def build_incomplete_year_case():
    year = 2005
    monthly_values = [2.0] * 12
    monthly_values[4] = None  # mayo ausente
    monthly_values[1] = 0.0  # febrero: cero valido, no ausente
    valid_months = sum(1 for v in monthly_values if v is not None)
    payload = {
        "case_id": "incomplete_year",
        "synthetic": True,
        "status": "anio_incompleto",
        "status_note": "Un mes ausente deja el anio sin los 12 meses validos exigidos; el cero de febrero sigue siendo valido.",
        "unit": "mm/day",
        "input": {
            "variable": "PRECTOTCORR",
            "year": year,
            "monthly_values": monthly_values,
        },
        "expected": {
            "valid_months": valid_months,
            "year_complete": valid_months == 12,
            "zero_counts_as_valid": monthly_values[1] == 0.0,
        },
    }
    write_fixture("incomplete_year", payload)
    return payload, valid_months


# ---------------------------------------------------------------------------
# Caso 6: cobertura de dos celdas de una misma region
# ---------------------------------------------------------------------------
def build_regional_coverage_case():
    cells_both_present = [
        {"cell_id": "cr_pn_cell_01", "region_id": "CR_PN", "weight": 1.0, "value": 10.0},
        {"cell_id": "cr_pn_cell_02", "region_id": "CR_PN", "weight": 3.0, "value": 14.0},
    ]
    mean_both, coverage_both = weighted_mean(
        [c["value"] for c in cells_both_present], [c["weight"] for c in cells_both_present]
    )

    cells_missing = [
        cells_both_present[0].copy(),
        {**cells_both_present[1], "value": None},
    ]
    mean_missing, coverage_missing = weighted_mean(
        [c["value"] for c in cells_missing], [c["weight"] for c in cells_missing]
    )

    payload = {
        "case_id": "regional_coverage",
        "synthetic": True,
        "status": "ver_scenarios",
        "status_note": "Dos escenarios: ambas celdas presentes (promedio valido) y la segunda celda ausente (promedio ausente).",
        "unit": "degC",
        "input": {
            "variable": "T2M",
            "scenario_both_cells_present": cells_both_present,
            "scenario_second_cell_missing": cells_missing,
        },
        "expected": {
            "both_cells_present": {
                "weighted_mean": mean_both,
                "coverage": coverage_both,
            },
            "second_cell_missing": {
                "weighted_mean": mean_missing,
                "coverage": coverage_missing,
                "mean_is_absent_below_threshold": mean_missing is None,
            },
        },
    }
    write_fixture("regional_coverage", payload)
    return payload, (mean_both, coverage_both, mean_missing, coverage_missing)


# ---------------------------------------------------------------------------
# Caso 7: bisiesto
# ---------------------------------------------------------------------------
def build_leap_year_case():
    years = [1999, 2000]
    results = {}
    for year in years:
        monthly_values = [2.0] * 12
        days = [days_in_month(year, m) for m in range(1, 13)]
        total_days = days_in_year(year)
        annual_rate = sum(d * v for d, v in zip(days, monthly_values)) / total_days
        accumulated = sum(d * v for d, v in zip(days, monthly_values))
        results[str(year)] = {
            "total_days": total_days,
            "annual_rate_mm_per_day": annual_rate,
            "annual_total_mm_per_year": accumulated,
        }
    payload = {
        "case_id": "leap_year_precip",
        "synthetic": True,
        "status": "referencia_agregacion_anual",
        "status_note": "Solo 2 anios: muy por debajo del minimo descriptivo (10) y de inferencia (30); se usa unicamente para contrastar la aritmetica de dias.",
        "unit": "mm/day",
        "unit_annual": "mm/yr",
        "input": {
            "variable": "PRECTOTCORR",
            "years": years,
            "monthly_value_constant": 2.0,
        },
        "expected": results,
    }
    write_fixture("leap_year_precip", payload)
    return payload, results


# ---------------------------------------------------------------------------
# Caso 8: constante
# ---------------------------------------------------------------------------
def build_constant_case():
    years = list(range(1990, 2020))
    values = [730.0] * len(years)
    ts = [float(t) for t in range(len(years))]
    b, a = ols_centered_sums(ts, values)
    payload = {
        "case_id": "constant_precip",
        "synthetic": True,
        "status": "descriptivo_ajuste_exacto",
        "status_note": "Serie constante: covarianza degenerada, pendiente y cambio cero, inferencia ausente.",
        "unit": "mm/yr",
        "unit_slope": "mm/yr/decade",
        "input": {
            "variable": "PRECTOTCORR",
            "years": years,
            "annual_values": values,
        },
        "expected": {
            "slope_per_year": b,
            "slope_per_decade": 10 * b,
            "adjusted_change": b * (ts[-1] - ts[0]),
            "inference": "ausente",
        },
    }
    write_fixture("constant_precip", payload)
    return payload, b


# ---------------------------------------------------------------------------
# Caso 9: BY
# ---------------------------------------------------------------------------
def build_by_case():
    entries = [
        {"key": "T2M:CR_PN", "region_id": "CR_PN", "variable": "T2M", "p": 0.001},
        {"key": "T2M:CR_CAR", "region_id": "CR_CAR", "variable": "T2M", "p": 0.04},
        {"key": "PRECTOTCORR:CR_PN", "region_id": "CR_PN", "variable": "PRECTOTCORR", "p": 0.02},
        {"key": "PRECTOTCORR:CR_CAR", "region_id": "CR_CAR", "variable": "PRECTOTCORR", "p": 0.20},
    ]
    pvals = [e["p"] for e in entries]
    q = fdr_by(pvals)

    # Invarianza ante permutacion: mismo resultado por llave, en otro orden de entrada.
    permuted_entries = [entries[2], entries[0], entries[3], entries[1]]
    permuted_pvals = [e["p"] for e in permuted_entries]
    permuted_q = fdr_by(permuted_pvals)
    q_by_key = {e["key"]: value for e, value in zip(entries, q)}
    permuted_q_by_key = {e["key"]: value for e, value in zip(permuted_entries, permuted_q)}
    permutation_invariant = all(
        approx(q_by_key[k], permuted_q_by_key[k]) for k in q_by_key
    )

    payload = {
        "case_id": "by_correction",
        "synthetic": True,
        "status": "familia_regional_v2",
        "status_note": "Cuatro pruebas regionales de la misma ventana: dos variables por dos regiones. Todos los p son evaluables.",
        "unit": "p_value",
        "input": {
            "family_id": "regions|T2M+PRECTOTCORR|CR_PN+CR_CAR|1990-2019|v2",
            "entries": entries,
        },
        "expected": {
            "q_by_key": q_by_key,
            "q_in_original_order": q,
            "permutation_invariant": permutation_invariant,
        },
        "independent_reference": {
            "method": "fdr_by manual: q_i = min(1, min_{j>=i}[m*H_m*p_j/j]), H_m = suma(1/k, k=1..m)",
            "m": len(entries),
            "H_m": sum(1.0 / k for k in range(1, len(entries) + 1)),
        },
    }
    write_fixture("by_correction", payload)
    return payload


# ---------------------------------------------------------------------------
# Caso 10: anomalia
# ---------------------------------------------------------------------------
def build_anomaly_case():
    case_a = {"observed": 12.0, "reference_mean": 10.0}
    anomaly_a = case_a["observed"] - case_a["reference_mean"]
    case_b = {"observed": 12.0, "reference_mean": None}
    anomaly_b = None

    payload = {
        "case_id": "anomaly_enso",
        "synthetic": True,
        "status": "ver_scenarios",
        "status_note": "Caso A: referencia disponible. Caso B: referencia ausente, la anomalia queda ausente (no se asume 0).",
        "unit": "degC",
        "input": {
            "variable": "T2M",
            "month": "julio",
            "scenario_reference_available": case_a,
            "scenario_reference_missing": case_b,
        },
        "expected": {
            "anomaly_reference_available": anomaly_a,
            "anomaly_reference_missing": anomaly_b,
        },
    }
    write_fixture("anomaly_enso", payload)
    return payload, (anomaly_a, anomaly_b)


def main() -> None:
    increase = build_linear_case("linear_trend_increase", 1990, 30, 20.0, 0.02, "degC")
    decrease = build_linear_case("linear_trend_decrease", 1990, 30, 20.0, -0.03, "degC")
    _, seasonality_series = build_seasonality_case()
    ar1 = build_ar1_case()
    _, incomplete_valid_months = build_incomplete_year_case()
    _, (mean_both, cov_both, mean_missing, cov_missing) = build_regional_coverage_case()
    _, leap_results = build_leap_year_case()
    _, constant_slope = build_constant_case()
    by_case = build_by_case()
    _, (anomaly_a, anomaly_b) = build_anomaly_case()

    # Referencias numericas calculadas a mano para los casos sinteticos.
    check("aumento: pendiente por decada", increase["expected"]["slope_per_decade"], 0.20)
    check("aumento: cambio ajustado", increase["expected"]["adjusted_change"], 0.58)
    check("disminucion: pendiente por decada", decrease["expected"]["slope_per_decade"], -0.30)
    check("disminucion: cambio ajustado", decrease["expected"]["adjusted_change"], -0.87)

    for v in seasonality_series:
        check("estacionalidad: media anual == 15", v, 15.0)

    check("AR(1): reproducible con semilla 42", ar1["expected"]["reproducible_with_seed_42"], True)
    check(
        "AR(1): cruce de formulas OLS coincide",
        ar1["independent_reference"]["slope_cross_check"],
        ar1["expected"]["slope_per_year_ols_centered_sums"],
    )

    check("ano incompleto: meses validos", incomplete_valid_months, 11)

    check("cobertura regional: media con ambas celdas", mean_both, 13.0)
    check("cobertura regional: cobertura con ambas celdas", cov_both, 1.0)
    check("cobertura regional: media ausente al faltar una celda", mean_missing, None)
    check("cobertura regional: cobertura 25% al faltar una celda", cov_missing, 0.25)

    check("bisiesto: tasa anual 1999", leap_results["1999"]["annual_rate_mm_per_day"], 2.0)
    check("bisiesto: tasa anual 2000", leap_results["2000"]["annual_rate_mm_per_day"], 2.0)
    check("bisiesto: acumulado 1999", leap_results["1999"]["annual_total_mm_per_year"], 730.0)
    check("bisiesto: acumulado 2000", leap_results["2000"]["annual_total_mm_per_year"], 732.0)

    check("constante: pendiente cero", constant_slope, 0.0)

    by_q = by_case["expected"]["q_by_key"]
    check("BY: q T2M:CR_PN", by_q["T2M:CR_PN"], 1 / 120)
    check("BY: q T2M:CR_CAR", by_q["T2M:CR_CAR"], 1 / 9)
    check("BY: q PRECTOTCORR:CR_PN", by_q["PRECTOTCORR:CR_PN"], 1 / 12)
    check("BY: q PRECTOTCORR:CR_CAR", by_q["PRECTOTCORR:CR_CAR"], 5 / 12)
    check("BY: invarianza ante permutacion", by_case["expected"]["permutation_invariant"], True)

    check("anomalia: +2 con referencia disponible", anomaly_a, 2.0)
    check("anomalia: ausente sin referencia", anomaly_b, None)

    print("\n".join(CHECKS))
    print(f"\n{len(CHECKS)} comprobaciones, todas OK.")


if __name__ == "__main__":
    main()
