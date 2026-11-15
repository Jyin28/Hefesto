"""Comparacion historica, OLS+HAC y BY regional (Hefesto v2, Entrega 2 EMANUEL).

Propietario: Emanuel. Normative source: docs/PLAN-HEFESTO.md, secciones 2, 3 y 6
("2. Comparacion automatica"; "3. Tendencia, incertidumbre y significancia",
puntos "OLS", "HAC de Newey-Garcia" y "Benjamini-Yekutieli (BY)"). Pure
stdlib, sin I/O al importar: misma convencion que `src/contracts.py` y
`src/prepare.py`. Sin numpy/scipy: la funcion beta incompleta regularizada
(para la referencia t de HAC) se implementa con fraccion continua
(Numerical Recipes `betacf`) sobre `math.lgamma`, que si es stdlib.

Entrada esperada: `annual_rows`, la salida de
`src/prepare.py::build_regional_annual` (o cualquier `list[dict]` con la misma
forma): cada fila con `region_id`, `variable`, `year`, `value` (float o `None`
si el anio no tiene los 12 meses validos). Este modulo no agrega mensual a
anual ni hace I/O; solo consume series anuales ya preparadas.

Resolucion de region (todas las funciones de ventana): si `region_id` se
omite, la serie usada debe venir de una sola region sin ambiguedad. Para
`compute_window_stats`/`compute_long_term_trend` eso se exige dentro de su
propia ventana; para `compare_historical_windows` se exige sobre las DOS
ventanas juntas (A y B), porque una region distinta por ventana compararia
dos regiones entre si sin que el llamador lo pidiera. Tambien se rechaza
cualquier anio duplicado dentro de la serie seleccionada (nunca se promedia
en silencio entre duplicados).

Regla de ventanas por defecto (PLAN-HEFESTO seccion 2, fila "Tendencia
historica"): dos bloques consecutivos, de igual duracion, sin solapamiento,
dentro de la cobertura. Con un numero impar de anios se excluye el mas
antiguo del valor por defecto. Para 1981-2024 esto da 1981-2002 y 2003-2024.
Se permiten ventanas explicitas dentro de la cobertura (`window_a`/`window_b`,
cada una validada contra `coverage_start_year`/`coverage_end_year`); en ese
caso no se exige igual duracion ni ausencia de huecos. El modulo conserva las
fechas solicitadas: una ventana con huecos no se recorta a los anios validos,
solo cuenta y reporta cuantos de sus anios tienen valor.

OLS descriptivo (PLAN-HEFESTO seccion 3, "OLS"): con menos de 10 anios validos
en la ventana, "datos insuficientes" (`level="none"`, `status="insufficient_data"`,
sin pendiente). Con 10 o mas, al menos "tendencia descriptiva"
(`level="descriptive"`, `status="ok"`): pendiente OLS por decada y cambio
ajustado entre el primer y el ultimo anio usados, ajustando con anios
calendario reales (no con un indice 0..n-1), para que un hueco dentro de la
ventana no comprima el eje temporal.

HAC de Newey-West (PLAN-HEFESTO seccion 3, "HAC"; vista "Evidencia de largo
plazo" de la seccion 2): con al menos `LONG_TERM_MIN_YEARS` (30) anios
validos y CONSECUTIVOS (sin huecos) dentro de la ventana, intenta inferencia:
nucleo Bartlett, `HAC_MAIN_LAGS` (3) rezagos, correccion de muestra pequena
(`n/(n-k)`, k=2 parametros) y referencia t-Student (grados de libertad n-2)
para el IC individual del 95 % y el p bilateral. Si el ajuste resulta
degenerado (varianza HAC numericamente nula, p. ej. una recta exacta o una
serie constante) o la ventana no tiene los 30 anios consecutivos, conserva la
magnitud OLS descriptiva (`level="descriptive"`) en vez de publicar
inferencia. `HAC_SENSITIVITY_LAGS` (1 y 5) se reportan aparte, sin cambiar la
pendiente (que no depende de L).

BY regional (PLAN-HEFESTO seccion 3, "BY", fila "pruebas de promedios
regionales"): las 4 combinaciones variable x region (`VARIABLE_IDS` x
`REGION_IDS`) de una misma ventana forman una familia; Benjamini-Yekutieli se
aplica una sola vez, despues de reunir todos los p validos (los de nivel
inferencial) de la familia COMPLETA. Filtrar esa familia para mostrar solo
una region o variable (`filter_family`) nunca recalcula el ajuste: conserva
los `p_adjusted` ya fijados.

Este modulo no calcula Sen/Mann-Kendall (Entrega EMANUEL-04/07).

--------------------------------------------------------------------------- #
Firmas publicas que Jacky necesita para conectar el servicio real:

  default_windows(start_year=COVERAGE_START_YEAR, end_year=COVERAGE_END_YEAR)
      -> tuple[tuple[int, int], tuple[int, int]]
    Division automatica de una cobertura en (ventana_a, ventana_b).

  compute_window_stats(annual_rows, start_year, end_year, *, variable,
                        region_id=None) -> WindowStats
    Estadisticas descriptivas de UNA ventana (promedio, anios usados,
    pendiente OLS si hay >= 10 anios validos). Ver guardas de region/
    duplicados en la nota de arriba.

  compare_historical_windows(annual_rows, *, variable, region_id=None,
                              window_a=None, window_b=None,
                              coverage_start_year=COVERAGE_START_YEAR,
                              coverage_end_year=COVERAGE_END_YEAR)
      -> HistoricalComparison
    Compara dos ventanas (por defecto o explicitas, cada una validada contra
    coverage_start_year/coverage_end_year). Devuelve ambas ventanas y B-A de
    promedio y pendiente.

  compute_long_term_trend(annual_rows, start_year, end_year, *, variable,
                           region_id=None) -> LongTermTrend
    OLS + HAC de UNA ventana larga: `trend` es un `contracts.TrendResult`
    (listo para el contrato v2) y `sensitivity` trae la misma estimacion a
    `HAC_SENSITIVITY_LAGS` rezagos.

  compute_regional_family(annual_rows, start_year, end_year, *, alpha=0.05)
      -> RegionalFamily
    Las 4 combinaciones variable x region de una ventana, con `p_adjusted`
    BY ya fijado sobre la familia completa.

  filter_family(family, *, variable=None, region_id=None)
      -> tuple[TrendResult, ...]
    Subconjunto de `family.results` sin recalcular el ajuste BY.

  fdr_by(p_values) -> list[float]
    Benjamini-Yekutieli puro, mismo orden que la entrada.

  WindowStats / HistoricalComparison / HacSensitivity / LongTermTrend /
  RegionalFamily: dataclasses frozen, mismo patron que `contracts.TrendResult`
  (todos los campos obligatorios; opcionales son `None` -> `null` en JSON via
  `contracts.to_jsonable`/`to_json`).
--------------------------------------------------------------------------- #
"""
from __future__ import annotations

import dataclasses
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.contracts import (
    ANNUAL_UNITS,
    COVERAGE_END_YEAR,
    COVERAGE_START_YEAR,
    REGION_IDS,
    SLOPE_UNITS,
    VARIABLE_IDS,
    TrendResult,
    WEB_REGION_IDS,
    validate_query,
)

# Minimo de anios validos en una ventana para publicar pendiente OLS
# descriptiva (PLAN-HEFESTO seccion 3, "OLS"). Por debajo: "datos insuficientes".
MIN_YEARS_FOR_DESCRIPTIVE_SLOPE = 10

# Minimo de anios validos y consecutivos para intentar inferencia HAC
# (PLAN-HEFESTO seccion 3, "HAC"; seccion 2, "Evidencia de largo plazo").
LONG_TERM_MIN_YEARS = 30
HAC_MAIN_LAGS = 3
HAC_SENSITIVITY_LAGS = (1, 5)
HAC_REGRESSION_PARAMS = 2  # intercepto + pendiente (correccion de muestra pequena n/(n-k))
HAC_DEGENERATE_SE_TOL = 1e-9  # SE HAC por debajo de esto se trata como ajuste degenerado
CONFIDENCE_LEVEL = 0.95

# BY regional (PLAN-HEFESTO seccion 3, "BY"): alpha de la familia de 4 pruebas.
FAMILY_ALPHA = 0.05


@dataclass(frozen=True)
class WindowStats:
    """Estadisticas descriptivas de una ventana anual. Todos los campos obligatorios;
    los opcionales son `None` (p. ej. sin suficientes anios validos para la pendiente).
    """

    region_id: str | None
    variable: str
    start_year: int
    end_year: int
    years_used: tuple[int, ...]
    n_years: int
    first_used_year: int | None
    last_used_year: int | None
    mean: float | None
    unit: str
    slope_per_decade: float | None
    slope_unit: str
    total_change: float | None
    level: str  # "none" | "descriptive" (contracts.LEVELS)
    status: str  # "ok" | "insufficient_data" (contracts.STATUSES)
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalComparison:
    """Comparacion B-A de dos ventanas historicas (PLAN-HEFESTO seccion 2).

    `mean_diff_b_minus_a`/`slope_diff_b_minus_a` son `None` si falta alguna de
    las dos estimaciones correspondientes (p. ej. una ventana con <10 anios
    validos no aporta pendiente).
    """

    region_id: str | None
    variable: str
    window_a: WindowStats
    window_b: WindowStats
    mean_diff_b_minus_a: float | None
    slope_diff_b_minus_a: float | None
    uses_default_windows: bool


@dataclass(frozen=True)
class HacSensitivity:
    """Sensibilidad de la inferencia HAC a otros rezagos (PLAN-HEFESTO seccion 3,
    "Usar uno y cinco rezagos como sensibilidad"). La pendiente no cambia con
    `lags` (es la misma pendiente OLS); aqui solo varia SE/IC/p. Todos los
    campos salvo `lags` son `None` si ese rezago tambien resulta degenerado.
    """

    lags: int
    se_hac: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None


@dataclass(frozen=True)
class LongTermTrend:
    """Resultado de `compute_long_term_trend`: `trend` es un
    `contracts.TrendResult` (contrato v2) a `HAC_MAIN_LAGS` rezagos;
    `sensitivity` trae la misma estimacion a `HAC_SENSITIVITY_LAGS`.
    """

    trend: TrendResult
    sensitivity: tuple[HacSensitivity, ...]


@dataclass(frozen=True)
class RegionalFamily:
    """Familia BY de promedios regionales: las `len(VARIABLE_IDS) * len(REGION_IDS)`
    combinaciones variable x region de una ventana (PLAN-HEFESTO seccion 3,
    "BY", fila "pruebas de promedios regionales"). `results` sigue el orden
    de `variable in VARIABLE_IDS, region in REGION_IDS`; cada entrada ya trae
    su `p_adjusted`/`significant`/`family_id` fijados sobre la familia
    COMPLETA, nunca sobre un subconjunto filtrado despues (ver
    `filter_family`). Las entradas sin `p_value` (nivel no inferencial)
    quedan con `p_adjusted=None`: no entran a la correccion.
    """

    family_id: str
    start_year: int
    end_year: int
    planned_tests: int
    valid_tests: int
    alpha: float
    scope: str
    regions: tuple[str, ...]
    variables: tuple[str, ...]
    results: tuple[TrendResult, ...]


# --------------------------------------------------------------------------- #
# Seleccion de serie (compartida por ventanas simples y vista de largo plazo)
# --------------------------------------------------------------------------- #
def _select_window_series(
    annual_rows: list[dict[str, Any]],
    start_year: int,
    end_year: int,
    *,
    variable: str,
    region_id: str | None,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """Filtra `annual_rows` a [start_year, end_year] para `variable` (y
    `region_id` si se da), ordena por anio y devuelve solo los anios con
    `value` no nulo: (years_used, values_used), mismo orden.

    Lanza ValueError si `region_id` es `None` y la ventana tiene filas de mas
    de una region (nunca se promedia entre regiones en silencio), o si la
    serie resultante (ya fijada a una sola region) tiene un anio duplicado.
    """
    rows_in_window = [
        r for r in annual_rows if r["variable"] == variable and start_year <= r["year"] <= end_year
    ]
    if region_id is None:
        distinct_regions = {r.get("region_id") for r in rows_in_window}
        if len(distinct_regions) > 1:
            raise ValueError(
                f"La ventana {start_year}-{end_year} tiene filas de mas de una region "
                f"({sorted(str(r) for r in distinct_regions)}); indique region_id."
            )
    else:
        rows_in_window = [r for r in rows_in_window if r.get("region_id") == region_id]

    year_counts = Counter(r["year"] for r in rows_in_window)
    duplicate_years = sorted(year for year, count in year_counts.items() if count > 1)
    if duplicate_years:
        raise ValueError(
            f"annual_rows tiene anios duplicados en la ventana {start_year}-{end_year}: "
            f"{duplicate_years}."
        )

    valid = sorted(
        ((r["year"], r["value"]) for r in rows_in_window
         if r["value"] is not None and math.isfinite(r["value"])),
        key=lambda item: item[0],
    )
    years_used = tuple(year for year, _ in valid)
    values_used = tuple(value for _, value in valid)
    return years_used, values_used


# --------------------------------------------------------------------------- #
# OLS puro (sin incertidumbre)
# --------------------------------------------------------------------------- #
def _ols_fit(xs: list[float], ys: list[float]) -> tuple[float, float, list[float]]:
    """Pendiente, intercepto y residuos OLS por sumas centradas (misma formula
    que `tests/fixtures/stats/generate_and_verify.py::ols_centered_sums` y
    `src/service_mock.py::_ols_slope`). `xs` son anios calendario reales, no
    un indice 0..n-1: con huecos dentro de la ventana, usar el anio real
    evita comprimir el eje temporal.
    """
    n = len(xs)
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    sxx = sum((x - xbar) ** 2 for x in xs)
    sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = ybar - b * xbar
    residuals = [y - (a + b * x) for x, y in zip(xs, ys)]
    return b, a, residuals


# --------------------------------------------------------------------------- #
# Referencia t-Student (beta incompleta regularizada, Numerical Recipes)
# --------------------------------------------------------------------------- #
def _betacf(a: float, b: float, x: float, *, max_iter: int = 200, eps: float = 3e-14) -> float:
    """Fraccion continua de la funcion beta incompleta (Numerical Recipes `betacf`)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betainc(x: float, a: float, b: float) -> float:
    """Funcion beta incompleta regularizada I_x(a, b), x en [0, 1]."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - ln_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_two_sided_p(t: float, df: float) -> float:
    """P(|T| > |t|) para T ~ t-Student(df). Identidad: I_{df/(df+t^2)}(df/2, 1/2)."""
    t = abs(t)
    x = df / (df + t * t)
    return _betainc(x, df / 2.0, 0.5)


def _t_critical_value(confidence: float, df: float, *, tol: float = 1e-10, max_iter: int = 200) -> float:
    """t* tal que P(|T| > t*) == 1 - confidence (referencia t para el IC individual).
    Por bisección sobre `_t_two_sided_p`, monotona decreciente en |t|.
    """
    alpha = 1.0 - confidence
    lo, hi = 0.0, 1.0
    while _t_two_sided_p(hi, df) > alpha:
        hi *= 2.0
        if hi > 1e8:
            break
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        p_mid = _t_two_sided_p(mid, df)
        if abs(p_mid - alpha) < tol:
            return mid
        if p_mid > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# --------------------------------------------------------------------------- #
# HAC de Newey-West (nucleo Bartlett, correccion de muestra pequena)
# --------------------------------------------------------------------------- #
def _hac_variance_per_year(xs: list[float], residuals: list[float], *, lags: int) -> float:
    """Varianza HAC (Newey-West, nucleo Bartlett) de la pendiente OLS por anio."""
    n = len(xs)
    xbar = sum(xs) / n
    z = [(x - xbar) * u for x, u in zip(xs, residuals)]
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0
    total = sum(zt * zt for zt in z)
    for lag in range(1, lags + 1):
        if lag >= n:
            break
        weight = 1.0 - lag / (lags + 1.0)
        cross = sum(z[t] * z[t - lag] for t in range(lag, n))
        total += 2.0 * weight * cross
    return total / (sxx * sxx)


def _hac_small_sample_correction(n: int, *, k_params: int = HAC_REGRESSION_PARAMS) -> float:
    """Factor n/(n-k) (misma convencion que `statsmodels.cov_hac(use_correction='hac')`)."""
    denom = n - k_params
    if denom <= 0:
        return 1.0
    return n / denom


def _hac_inference(
    xs: list[float], residuals: list[float], slope_per_year: float, *, lags: int, scale: float = 1.0
) -> dict[str, float] | None:
    """SE/IC/p de la pendiente (por decada) con HAC a `lags` rezagos. `None` si
    degenerado (SE numericamente nulo: no se puede dividir, solo la magnitud
    OLS queda identificable).
    """
    n = len(xs)
    var_py = _hac_variance_per_year(xs, residuals, lags=lags) * _hac_small_sample_correction(n)
    se_per_year = math.sqrt(var_py) if var_py > 0.0 else 0.0
    # Tolerancia relativa a la escala de la serie (mm/yr vs degC), no absoluta.
    if se_per_year < HAC_DEGENERATE_SE_TOL * max(1.0, scale):
        return None
    se_decade = se_per_year * 10.0
    df = n - HAC_REGRESSION_PARAMS
    t_stat = slope_per_year / se_per_year
    p_value = _t_two_sided_p(t_stat, df)
    t_crit = _t_critical_value(CONFIDENCE_LEVEL, df)
    slope_decade = slope_per_year * 10.0
    return {
        "se_hac": se_decade,
        "p_value": p_value,
        "ci_low": slope_decade - t_crit * se_decade,
        "ci_high": slope_decade + t_crit * se_decade,
    }


# --------------------------------------------------------------------------- #
# Ventanas por defecto / explicitas
# --------------------------------------------------------------------------- #
def default_windows(
    start_year: int = COVERAGE_START_YEAR, end_year: int = COVERAGE_END_YEAR
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Divide [start_year, end_year] en dos bloques consecutivos de igual
    duracion y sin solapamiento. Con numero impar de anios, excluye el mas
    antiguo. Para (1981, 2024) devuelve ((1981, 2002), (2003, 2024)).
    """
    if start_year > end_year:
        raise ValueError(f"Rango invalido: start_year {start_year} > end_year {end_year}.")
    total_years = end_year - start_year + 1
    if total_years < 2:
        raise ValueError(
            f"Cobertura {start_year}-{end_year} ({total_years} anio(s)) no alcanza "
            "para dos ventanas (se necesita al menos 1 anio por ventana)."
        )
    effective_start = start_year
    if total_years % 2 == 1:
        effective_start = start_year + 1
        total_years -= 1
    half = total_years // 2
    window_a = (effective_start, effective_start + half - 1)
    window_b = (effective_start + half, end_year)
    return window_a, window_b


def compute_window_stats(
    annual_rows: list[dict[str, Any]],
    start_year: int,
    end_year: int,
    *,
    variable: str,
    region_id: str | None = None,
) -> WindowStats:
    """Promedio, anios usados y (si hay >= `MIN_YEARS_FOR_DESCRIPTIVE_SLOPE`
    anios validos) pendiente OLS descriptiva de una ventana. `start_year`/
    `end_year` se conservan tal como se pidieron: si la serie tiene huecos,
    `years_used` queda mas corto pero la ventana reportada no se recorta.
    Ver `_select_window_series` para las guardas de region/duplicados.
    """
    validate_query(variable, region_id, start_year, end_year, regions=WEB_REGION_IDS)
    unit = ANNUAL_UNITS[variable]
    slope_unit = SLOPE_UNITS[variable]

    years_used, values_used = _select_window_series(
        annual_rows, start_year, end_year, variable=variable, region_id=region_id
    )
    n_years = len(years_used)
    expected_years = end_year - start_year + 1

    warnings: list[str] = []
    if n_years == 0:
        warnings.append("no_data")
    elif n_years < expected_years:
        warnings.append("temporal_gaps")

    mean = sum(values_used) / n_years if n_years > 0 else None
    first_used_year = years_used[0] if years_used else None
    last_used_year = years_used[-1] if years_used else None

    if n_years < MIN_YEARS_FOR_DESCRIPTIVE_SLOPE:
        level = "none"
        status = "insufficient_data"
        slope_per_decade = None
        total_change = None
        if n_years > 0:
            warnings.append("short_record")
    else:
        level = "descriptive"
        status = "ok"
        xs = [float(year) for year in years_used]
        slope_per_year, _intercept, _residuals = _ols_fit(xs, list(values_used))
        slope_per_decade = slope_per_year * 10.0
        total_change = slope_per_year * (last_used_year - first_used_year)

    return WindowStats(
        region_id=region_id,
        variable=variable,
        start_year=start_year,
        end_year=end_year,
        years_used=years_used,
        n_years=n_years,
        first_used_year=first_used_year,
        last_used_year=last_used_year,
        mean=mean,
        unit=unit,
        slope_per_decade=slope_per_decade,
        slope_unit=slope_unit,
        total_change=total_change,
        level=level,
        status=status,
        warnings=tuple(warnings),
    )


def compare_historical_windows(
    annual_rows: list[dict[str, Any]],
    *,
    variable: str,
    region_id: str | None = None,
    window_a: tuple[int, int] | None = None,
    window_b: tuple[int, int] | None = None,
    coverage_start_year: int = COVERAGE_START_YEAR,
    coverage_end_year: int = COVERAGE_END_YEAR,
) -> HistoricalComparison:
    """Compara dos ventanas historicas de `annual_rows` (PLAN-HEFESTO seccion 2).

    Sin `window_a`/`window_b`, se usa `default_windows(coverage_start_year,
    coverage_end_year)`. Ambas deben darse juntas para fijar ventanas
    explicitas (no se exige igual duracion ni ausencia de solapamiento en ese
    caso, a diferencia del valor por defecto); cada una debe caer dentro de
    `coverage_start_year`/`coverage_end_year`.

    Si `region_id` se omite, se resuelve UNA sola region para ambas ventanas
    juntas: si A y B tienen filas de regiones distintas (p. ej. A solo
    `CR_PN` y B solo `CR_CAR`), cada ventana por separado no es ambigua pero
    la comparacion si lo seria (compararia dos regiones entre si sin que se
    pidiera), asi que se exige `region_id` explicito.
    """
    if variable not in VARIABLE_IDS:
        raise ValueError(f"Variable invalida: {variable!r}. Validas: {', '.join(VARIABLE_IDS)}.")

    uses_default = window_a is None and window_b is None
    if uses_default:
        validate_query(variable, region_id, coverage_start_year, coverage_end_year, regions=WEB_REGION_IDS)
        window_a, window_b = default_windows(coverage_start_year, coverage_end_year)
    elif window_a is None or window_b is None:
        raise ValueError(
            "Se requieren window_a y window_b juntas (ventanas explicitas) o ninguna "
            "(usa el valor por defecto sobre coverage_start_year/coverage_end_year)."
        )
    else:
        for label, window in (("window_a", window_a), ("window_b", window_b)):
            w_start, w_end = window
            if w_start < coverage_start_year or w_end > coverage_end_year:
                raise ValueError(
                    f"{label} {w_start}-{w_end} fuera de la cobertura "
                    f"{coverage_start_year}-{coverage_end_year} (inclusive)."
                )

    if region_id is None:
        candidates = {
            r.get("region_id")
            for start, end in (window_a, window_b)
            for r in annual_rows
            if r["variable"] == variable and start <= r["year"] <= end
        }
        if len(candidates) > 1:
            raise ValueError(
                "Las ventanas A y B tienen filas de mas de una region "
                f"({sorted(str(c) for c in candidates)}); indique region_id."
            )

    stats_a = compute_window_stats(annual_rows, window_a[0], window_a[1], variable=variable, region_id=region_id)
    stats_b = compute_window_stats(annual_rows, window_b[0], window_b[1], variable=variable, region_id=region_id)

    mean_diff = (
        stats_b.mean - stats_a.mean if stats_a.mean is not None and stats_b.mean is not None else None
    )
    slope_diff = (
        stats_b.slope_per_decade - stats_a.slope_per_decade
        if stats_a.slope_per_decade is not None and stats_b.slope_per_decade is not None
        else None
    )

    return HistoricalComparison(
        region_id=region_id,
        variable=variable,
        window_a=stats_a,
        window_b=stats_b,
        mean_diff_b_minus_a=mean_diff,
        slope_diff_b_minus_a=slope_diff,
        uses_default_windows=uses_default,
    )


# --------------------------------------------------------------------------- #
# Evidencia de largo plazo: OLS + HAC
# --------------------------------------------------------------------------- #
def compute_long_term_trend(
    annual_rows: list[dict[str, Any]],
    start_year: int,
    end_year: int,
    *,
    variable: str,
    region_id: str | None = None,
) -> LongTermTrend:
    """OLS + HAC de una ventana larga (PLAN-HEFESTO seccion 2 "Evidencia de
    largo plazo" y seccion 3 "OLS"/"HAC"). Requiere al menos
    `LONG_TERM_MIN_YEARS` anios validos y CONSECUTIVOS (sin huecos) dentro de
    la ventana para intentar inferencia; si el ajuste HAC resulta degenerado
    (varianza nula, p. ej. una recta exacta o una serie constante), conserva
    la magnitud OLS y queda en "descriptive" en vez de "inferential". Con
    menos de 10 anios validos, "insufficient_data" (igual que
    `compute_window_stats`).
    """
    validate_query(variable, region_id, start_year, end_year, regions=WEB_REGION_IDS)
    unit_slope = SLOPE_UNITS[variable]
    expected_years = end_year - start_year + 1

    years_used, values_used = _select_window_series(
        annual_rows, start_year, end_year, variable=variable, region_id=region_id
    )
    n_years = len(years_used)
    first_used_year = years_used[0] if years_used else None
    last_used_year = years_used[-1] if years_used else None
    # coverage_fraction = fraccion de peso de mascara elegible (plan v2 s.3.1), no fraccion de anios.
    window_rows = [r for r in annual_rows if r["variable"] == variable and start_year <= r["year"] <= end_year
                   and (region_id is None or r.get("region_id") == region_id)]
    coverages = [r["mean_monthly_coverage"] for r in window_rows if r.get("mean_monthly_coverage") is not None]
    coverage_fraction = min(coverages) if coverages else (1.0 if n_years else 0.0)
    coverage_failed = any("coverage_failure" in (r.get("warnings") or ()) for r in window_rows)

    if n_years < MIN_YEARS_FOR_DESCRIPTIVE_SLOPE:
        warnings = ["no_data"] if n_years == 0 else ["short_record"]
        if coverage_failed:
            warnings.append("coverage_failure")
        trend = TrendResult(
            region_id=region_id, variable=variable, start_year=start_year, end_year=end_year,
            first_used_year=first_used_year, last_used_year=last_used_year, n_years=n_years,
            level="none", status="insufficient_data", slope_per_decade=None, slope_unit=unit_slope,
            total_change=None, ci_low=None, ci_high=None, se_hac=None, p_value=None,
            p_adjusted=None, significant=None, family_id=None, hac_lags=None,
            method="sin ajuste (n<10)", coverage_fraction=coverage_fraction, warnings=tuple(warnings),
        )
        return LongTermTrend(trend, ())

    xs = [float(year) for year in years_used]
    ys = list(values_used)
    slope_per_year, _intercept, residuals = _ols_fit(xs, ys)
    slope_per_decade = slope_per_year * 10.0
    total_change = slope_per_year * (last_used_year - first_used_year)
    scale = max(abs(v) for v in ys)

    consecutive = (last_used_year - first_used_year + 1) == n_years
    warnings: list[str] = []
    if not consecutive:
        warnings.append("temporal_gaps")
    if n_years < expected_years:
        warnings.append("incomplete_years")

    eligible_for_inference = n_years >= LONG_TERM_MIN_YEARS and consecutive
    sensitivity: list[HacSensitivity] = []
    main_result: dict[str, float] | None = None
    if eligible_for_inference:
        main_result = _hac_inference(xs, residuals, slope_per_year, lags=HAC_MAIN_LAGS, scale=scale)
        for lags in HAC_SENSITIVITY_LAGS:
            result = _hac_inference(xs, residuals, slope_per_year, lags=lags, scale=scale)
            sensitivity.append(
                HacSensitivity(
                    lags=lags,
                    se_hac=result["se_hac"] if result else None,
                    ci_low=result["ci_low"] if result else None,
                    ci_high=result["ci_high"] if result else None,
                    p_value=result["p_value"] if result else None,
                )
            )

    if main_result is not None:
        level, status = "inferential", "ok"
        se_hac, p_value = main_result["se_hac"], main_result["p_value"]
        ci_low, ci_high, hac_lags = main_result["ci_low"], main_result["ci_high"], HAC_MAIN_LAGS
        method = "OLS + HAC Newey-West (Bartlett, L=3, correccion de muestra pequena)"
    else:
        level, status = "descriptive", "ok"
        se_hac = p_value = ci_low = ci_high = hac_lags = None
        method = "OLS descriptivo"
        if eligible_for_inference:
            warnings.append("degenerate_series")
        else:
            warnings.append("short_for_inference")

    trend = TrendResult(
        region_id=region_id, variable=variable, start_year=start_year, end_year=end_year,
        first_used_year=first_used_year, last_used_year=last_used_year, n_years=n_years,
        level=level, status=status, slope_per_decade=slope_per_decade, slope_unit=unit_slope,
        total_change=total_change, ci_low=ci_low, ci_high=ci_high, se_hac=se_hac, p_value=p_value,
        p_adjusted=None, significant=None, family_id=None, hac_lags=hac_lags, method=method,
        coverage_fraction=coverage_fraction, warnings=tuple(warnings),
    )
    return LongTermTrend(trend, tuple(sensitivity))


# --------------------------------------------------------------------------- #
# BY regional (familia de 4 pruebas: VARIABLE_IDS x REGION_IDS)
# --------------------------------------------------------------------------- #
def fdr_by(p_values: list[float]) -> list[float]:
    """Benjamini-Yekutieli, mismo orden que la entrada (replica
    `tests/fixtures/stats/generate_and_verify.py::fdr_by` y
    `src/service_mock.py::_by_adjust`).
    """
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    h_m = sum(1.0 / k for k in range(1, m + 1))
    ranked = [p_values[i] for i in order]
    raw = [min(1.0, m * h_m * ranked[j] / (j + 1)) for j in range(m)]
    q_sorted = [0.0] * m
    q_sorted[-1] = raw[-1]
    for j in range(m - 2, -1, -1):
        q_sorted[j] = min(raw[j], q_sorted[j + 1])
    q = [0.0] * m
    for rank_pos, orig_i in enumerate(order):
        q[orig_i] = q_sorted[rank_pos]
    return q


def regional_family_id(start_year: int, end_year: int) -> str:
    return f"regions|{'+'.join(VARIABLE_IDS)}|{'+'.join(REGION_IDS)}|{start_year}-{end_year}|v2"


def compute_regional_family(
    annual_rows: list[dict[str, Any]],
    start_year: int,
    end_year: int,
    *,
    alpha: float = FAMILY_ALPHA,
) -> RegionalFamily:
    """`compute_long_term_trend` sobre las 4 combinaciones (variable x region)
    de una ventana, con BY aplicado despues de reunir todos los p validos
    (los de nivel inferencial) de la familia completa.
    """
    combos = [(variable, region) for variable in VARIABLE_IDS for region in REGION_IDS]
    raw_trends = [
        compute_long_term_trend(annual_rows, start_year, end_year, variable=variable, region_id=region).trend
        for variable, region in combos
    ]
    valid_idx = [i for i, t in enumerate(raw_trends) if t.p_value is not None]
    q_values = fdr_by([raw_trends[i].p_value for i in valid_idx])
    fid = regional_family_id(start_year, end_year)

    results = list(raw_trends)
    for i, q in zip(valid_idx, q_values):
        results[i] = dataclasses.replace(raw_trends[i], p_adjusted=q, significant=q < alpha, family_id=fid)

    return RegionalFamily(
        family_id=fid,
        start_year=start_year,
        end_year=end_year,
        planned_tests=len(combos),
        valid_tests=len(valid_idx),
        alpha=alpha,
        scope="regions",
        regions=REGION_IDS,
        variables=VARIABLE_IDS,
        results=tuple(results),
    )


def filter_family(
    family: RegionalFamily, *, variable: str | None = None, region_id: str | None = None
) -> tuple[TrendResult, ...]:
    """Subconjunto de `family.results` por variable/region. Nunca recalcula
    BY: devuelve los mismos `p_adjusted` ya fijados sobre la familia completa
    (PLAN-HEFESTO seccion 3: "Filtrar el mapa conserva el ajuste original").
    """
    return tuple(
        t
        for t in family.results
        if (variable is None or t.variable == variable) and (region_id is None or t.region_id == region_id)
    )


# --------------------------------------------------------------------------- #
# Diagnostico de homogeneidad (cambio de nivel): Pettitt sobre residuos OLS
# --------------------------------------------------------------------------- #
HOMOGENEITY_ALPHA = 0.05
HOMOGENEITY_MIN_YEARS = 20


def homogeneity_check(
    annual_rows: list[dict[str, Any]], start_year: int, end_year: int, *, variable: str, region_id: str
) -> dict[str, Any]:
    """Prueba de Pettitt (no parametrica) de un salto de nivel en la serie anual.

    Se aplica a los RESIDUOS de la recta OLS para que una tendencia gradual no se confunda con un
    salto abrupto. p ~ 2 exp(-6 K^2 / (n^3 + n^2)) (aproximacion asintotica de Pettitt, 1979).
    Es un diagnostico de calidad de datos: NO oculta ni modifica la tendencia, y no distingue por si
    solo un cambio de fuente de un cambio climatico real. Se calcula igual para ambas variables.
    """
    validate_query(variable, region_id, start_year, end_year, regions=WEB_REGION_IDS)
    years, values = _select_window_series(annual_rows, start_year, end_year, variable=variable, region_id=region_id)
    n = len(years)
    result: dict[str, Any] = {
        "method": "Pettitt sobre residuos OLS", "alpha": HOMOGENEITY_ALPHA, "n_years": n,
        "status": "insufficient_data", "break_year": None, "p_value": None,
        "mean_before": None, "mean_after": None, "ratio_after_before": None,
        "possible_inhomogeneity": None,
    }
    if n < HOMOGENEITY_MIN_YEARS or (years[-1] - years[0] + 1) != n:
        return result
    xs = [float(y) for y in years]
    _slope, _intercept, residuals = _ols_fit(xs, list(values))
    best_k, best_t = -1.0, 0
    for t in range(n - 1):
        u = sum((residuals[i] > residuals[j]) - (residuals[i] < residuals[j])
                for i in range(t + 1) for j in range(t + 1, n))
        if abs(u) > best_k:
            best_k, best_t = abs(u), t
    p = min(1.0, 2.0 * math.exp(-6.0 * best_k ** 2 / (n ** 3 + n ** 2)))
    before, after = values[: best_t + 1], values[best_t + 1:]
    mean_before, mean_after = sum(before) / len(before), sum(after) / len(after)
    result.update(
        status="ok", break_year=years[best_t + 1], p_value=p, mean_before=mean_before, mean_after=mean_after,
        ratio_after_before=(mean_after / mean_before) if mean_before else None,
        possible_inhomogeneity=p < HOMOGENEITY_ALPHA,
    )
    return result
