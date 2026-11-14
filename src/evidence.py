"""Independent trend check and multiple-testing families for Detective Tico."""
from collections import Counter
from dataclasses import replace
from math import erfc, sqrt
from statistics import mean, median

from .contracts import REGION_IDS, SLOPE_UNITS, VARIABLE_IDS, validate_query
from .statistics import (
    LONG_TERM_MIN_YEARS, MIN_YEARS_FOR_DESCRIPTIVE_SLOPE, _select_window_series,
    compute_long_term_trend, fdr_by, homogeneity_check,
)


def _midranks(values):
    counts = Counter(values)
    ranks = {}
    offset = 0
    for value, count in sorted(counts.items()):
        ranks[value] = offset + (count + 1) / 2
        offset += count
    return [ranks[value] for value in values]


def sen_mann_kendall(rows, start, end, variable, region):
    """Sen and bilateral MK with tie correction and Hamed–Rao rank screening."""
    validate_query(variable, region, start, end)
    years, values = _select_window_series(rows, start, end, variable=variable, region_id=region)
    n = len(years)
    result = dict(
        method="Sen + Mann–Kendall (Hamed–Rao)", screening_alpha=0.05,
        max_lag=max(0, n - 3), lags_used=[], n_years=n, slope_per_decade=None,
        slope_unit=SLOPE_UNITS[variable], score=None, variance=None, p_value=None,
        p_adjusted=None, significant=None, family_id=None, status="insufficient_data",
    )
    if n < MIN_YEARS_FOR_DESCRIPTIVE_SLOPE:
        return result
    pairs = [(j, i) for j in range(n) for i in range(j)]
    slope = median((values[j] - values[i]) / (years[j] - years[i]) for j, i in pairs)
    result.update(slope_per_decade=10 * slope, status="descriptive")
    if n < LONG_TERM_MIN_YEARS or years[-1] - years[0] + 1 != n:
        return result

    score = sum((values[j] > values[i]) - (values[j] < values[i]) for j, i in pairs)
    tie_term = sum(c * (c - 1) * (2 * c + 5) for c in Counter(values).values())
    variance = (n * (n - 1) * (2 * n + 5) - tie_term) / 18
    if variance <= 0:
        return result

    detrended = [value - slope * (year - years[0]) for year, value in zip(years, values)]
    ranks = _midranks(detrended)
    rank_mean = mean(ranks)
    centered = [rank - rank_mean for rank in ranks]
    sum_squares = sum(rank * rank for rank in centered)
    contribution = 0.0
    if sum_squares:
        bound = 1.959963984540054 / sqrt(n)
        for lag in range(1, n - 2):
            rho = sum(a * b for a, b in zip(centered, centered[lag:])) / sum_squares
            if abs(rho) > bound:
                result["lags_used"].append(lag)
                k = n - lag
                contribution += k * (k - 1) * (k - 2) * rho
    # Signed Hamed–Rao variance correction. A nonpositive estimate is unusable.
    variance *= 1 + 2 * contribution / (n * (n - 1) * (n - 2))
    if variance <= 0:
        result["status"] = "degenerate_variance"
        return result
    z = max(abs(score) - 1, 0) / sqrt(variance)
    return dict(result, score=score, variance=variance, p_value=erfc(z / sqrt(2)),
                status="inferential")


PRECIP_CAUTION = "reanalysis_precip_caution"


def _family_id(scope, variables, start, end, method):
    subject = "+".join(variables) if scope == "regions" else variables[0]
    suffix = "" if method == "ols" else "|mk"
    return f"{scope}|{subject}|{'+'.join(REGION_IDS)}|{start}-{end}|v2{suffix}"


def evidence_family(series, start, end, scope, variable=None):
    """Adjust all eligible tests before returning a filtered result to the UI.

    Regional family: 2 variables x 2 regions; map family: every eligible cell of BOTH sectors
    for one variable. The correction is fixed here, before any view filtering.
    """
    variables = (variable,) if variable else VARIABLE_IDS
    entries = {}
    for subject, (region, rows) in series.items():
        for var in variables:
            long_term = compute_long_term_trend(rows, start, end, variable=var, region_id=region)
            lag_p = {s.lags: s.p_value for s in long_term.sensitivity}
            main_p = long_term.trend.p_value
            changes = None
            if main_p is not None and lag_p and all(v is not None for v in lag_p.values()):
                changes = any((v < 0.05) != (main_p < 0.05) for v in lag_p.values())
            entries[subject, var] = {
                "ols": long_term.trend,
                "hac_sensitivity": long_term.sensitivity,
                "hac_sensitivity_changes_conclusion": changes,
                "mann_kendall": sen_mann_kendall(rows, start, end, var, region),
                "homogeneity": homogeneity_check(rows, start, end, variable=var, region_id=region),
            }

    families = {}
    for method in ("ols", "mann_kendall"):
        family_id = _family_id(scope, variables, start, end, method)
        eligible = []
        for entry in entries.values():
            result = entry[method]
            p = result.p_value if method == "ols" else result["p_value"]
            if p is not None:
                eligible.append((entry, p))
        for (entry, _), adjusted in zip(eligible, fdr_by([p for _, p in eligible])):
            fields = dict(p_adjusted=adjusted, significant=adjusted < 0.05, family_id=family_id)
            if method == "ols":
                entry[method] = replace(entry[method], **fields)
            else:
                entry[method].update(fields)
        families[method] = dict(family_id=family_id, scope=scope, variables=variables,
                                regions=REGION_IDS, planned_tests=len(entries),
                                valid_tests=len(eligible), alpha=0.05, method="fdr_by",
                                start_year=start, end_year=end)

    # Advertencias de calidad de datos: se anaden al TrendResult, nunca ocultan la tendencia.
    for (_, var), entry in entries.items():
        extra = []
        if entry["homogeneity"]["possible_inhomogeneity"]:
            extra.append("possible_inhomogeneity")
        if var == "PRECTOTCORR":
            extra.append(PRECIP_CAUTION)
        if extra:
            ols = entry["ols"]
            entry["ols"] = replace(ols, warnings=tuple(dict.fromkeys(ols.warnings + tuple(extra))))
    return entries, families
