"""Independent trend check and multiple-testing families for Detective Tico."""
from collections import Counter
from dataclasses import replace
from math import erfc, sqrt
from statistics import mean, median

from .contracts import REGION_IDS, SLOPE_UNITS, VARIABLE_IDS, validate_query
from .statistics import (
    LONG_TERM_MIN_YEARS, MIN_YEARS_FOR_DESCRIPTIVE_SLOPE, _select_window_series,
    compute_long_term_trend, fdr_by,
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


def evidence_family(series, start, end, scope, variable=None):
    """Adjust all eligible tests before returning a filtered result to the UI."""
    variables = (variable,) if variable else VARIABLE_IDS
    entries = {}
    for subject, (region, rows) in series.items():
        for var in variables:
            long_term = compute_long_term_trend(rows, start, end, variable=var, region_id=region)
            entries[subject, var] = {
                "ols": long_term.trend,
                "hac_sensitivity": long_term.sensitivity,
                "mann_kendall": sen_mann_kendall(rows, start, end, var, region),
            }

    families = {}
    for method in ("ols", "mann_kendall"):
        family_id = f"{scope}|{method}|{'+'.join(variables)}|{start}-{end}|v2"
        eligible = []
        for entry in entries.values():
            result = entry[method]
            p = result.p_value if method == "ols" else result["p_value"]
            if p is not None:
                eligible.append((entry, p))
        for (entry, _), adjusted in zip(eligible, fdr_by([p for _, p in eligible])):
            fields = dict(p_adjusted=adjusted, significant=adjusted <= 0.05, family_id=family_id)
            if method == "ols":
                entry[method] = replace(entry[method], **fields)
            else:
                entry[method].update(fields)
        families[method] = dict(family_id=family_id, scope=scope, variables=variables,
                                regions=REGION_IDS, planned_tests=len(entries),
                                valid_tests=len(eligible), alpha=0.05)
    return entries, families
