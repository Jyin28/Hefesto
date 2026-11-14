"""Documented ENSO cases and monthly anomalies against 1981–2010."""
from statistics import mean

from .prepare import days_in_month

MIN_BASELINE_YEARS = 24


def _month_index(date):
    year, month = map(int, date.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"Mes inválido: {date}")
    return year * 12 + month - 1


def episode_comparison(rows, variable, catalog, coverage_start, coverage_end):
    start_limit, end_limit = coverage_start * 12, coverage_end * 12 + 11
    episodes = [
        item for item in catalog["episodes"] if item["sources"]
        and start_limit <= _month_index(item["start"]) <= _month_index(item["end"]) <= end_limit
    ]
    if not episodes:
        return {"status": "episode_unavailable", "months": []}
    episode = max(episodes, key=lambda item: _month_index(item["end"]))
    start, end = map(_month_index, (episode["start"], episode["end"]))
    neutral = None
    for shift in range(12, start - start_limit + 1, 12):
        if end - shift >= start:
            continue
        for period in catalog["neutral_periods"]:
            if period["sources"] and _month_index(period["start"]) <= start - shift:
                if end - shift <= _month_index(period["end"]):
                    neutral = (shift, period["sources"])
                    break
        if neutral:
            break

    values = {}
    for row in rows:
        if row["variable"] != variable or row["value"] is None:
            continue
        year, month = row["year"], row["month"]
        factor = days_in_month(year, month) if variable == "PRECTOTCORR" else 1
        values[year * 12 + month - 1] = row["value"] * factor

    normals = {}
    normal_counts = {}
    for month in range(12):
        sample = [values[year * 12 + month] for year in range(1981, 2011)
                  if year * 12 + month in values]
        normal_counts[month] = len(sample)
        normals[month] = mean(sample) if len(sample) >= MIN_BASELINE_YEARS else None

    months = []
    for index in range(start, end + 1):
        year, month = divmod(index, 12)
        value = values.get(index)
        normal = normals[month]
        other = values.get(index - neutral[0]) if neutral else None
        months.append({
            "date": f"{year}-{month + 1:02d}", "value": value, "normal": normal, "neutral": other,
            "baseline_n_years": normal_counts[month],
            "anomaly": value - normal if value is not None and normal is not None else None,
            "vs_neutral": value - other if value is not None and other is not None else None,
        })
    return {
        "status": "ok" if neutral else "neutral_unverified",
        "episode": episode, "neutral_sources": neutral[1] if neutral else [],
        "neutral_year_shift": neutral[0] // 12 if neutral else None,
        "neutral_window": [
            f"{index // 12}-{index % 12 + 1:02d}" for index in (start - neutral[0], end - neutral[0])
        ] if neutral else None,
        "baseline": [1981, 2010], "unit": "mm/month" if variable == "PRECTOTCORR" else "degC",
        "baseline_min_years": MIN_BASELINE_YEARS,
        "months": months,
    }
