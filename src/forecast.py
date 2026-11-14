"""One-month station forecast with expanding chronological validation."""
from math import isfinite
from datetime import date as calendar_date
from statistics import mean


def evaluate_station(records, metadata, variable, *, min_training_years=10, min_validation_years=2):
    """Fit monthly climatology plus a lag-one anomaly; compare on identical dates."""
    if min_training_years < 1 or min_validation_years < 1:
        raise ValueError("Se requiere al menos un año para cada etapa")
    for field in ("station_id", "name", "latitude", "longitude", "source_url", "license", "unit"):
        if metadata.get(field) is None or metadata[field] == "":
            raise ValueError(f"Falta metadato de estación: {field}")
    expected_unit = {"T2M": "degC", "PRECTOTCORR": "mm/month"}[variable]
    if metadata["unit"] != expected_unit:
        raise ValueError(f"La unidad requerida es {expected_unit}")
    if not -90 <= float(metadata["latitude"]) <= 90 or not -180 <= float(metadata["longitude"]) <= 180:
        raise ValueError("Coordenadas de estación inválidas")
    observed = {}
    for record in records:
        year, month = int(record["year"]), int(record["month"])
        index = 12 * year + month - 1
        value = float(record["value"])
        if not 1 <= month <= 12 or index in observed or not isfinite(value):
            raise ValueError("Mes, duplicado o valor de estación inválido")
        if variable == "PRECTOTCORR" and value < 0:
            raise ValueError("La precipitación mensual no puede ser negativa")
        observed[index] = value
    if not observed:
        return {"status": "insufficient_station_data", "station": metadata}
    first, last = min(observed), max(observed)
    start_test = first + 12 * min_training_years
    test_months = list(range(start_test, last + 1))
    if len(test_months) < 12 * min_validation_years or len(observed) != last - first + 1:
        return {"status": "insufficient_station_data", "station": metadata}

    def predict(target):
        monthly = {
            month: mean(observed[i] for i in range(first, target) if i % 12 == month)
            for month in range(12)
        }
        anomalies = {i: observed[i] - monthly[i % 12] for i in range(first, target)}
        lag_square = sum(anomalies[i - 1] ** 2 for i in range(first + 1, target))
        beta = (sum(anomalies[i - 1] * anomalies[i] for i in range(first + 1, target))
                / lag_square) if lag_square else 0.0
        baseline = monthly[target % 12]
        value = baseline + beta * anomalies[target - 1]
        return max(0, value) if variable == "PRECTOTCORR" else value, baseline

    model_errors, baseline_errors = [], []
    for index in test_months:
        predicted, baseline = predict(index)
        model_errors.append(abs(observed[index] - predicted))
        baseline_errors.append(abs(observed[index] - baseline))
    model_mae, baseline_mae = mean(model_errors), mean(baseline_errors)
    target = last + 1

    def date(index):
        year, month = divmod(index, 12)
        return f"{year}-{month + 1:02d}"

    improved = model_mae < baseline_mae
    today = calendar_date.today()
    current = 12 * today.year + today.month - 1
    timely = target >= current
    approved = improved and timely
    status = "baseline_not_improved"
    if improved:
        status = "validated" if timely else "validated_historical"
    return {
        "status": status,
        "station": metadata, "unit": expected_unit, "target": date(target),
        "forecast": predict(target)[0] if approved else None,
        "message": ("El mes objetivo ya pasó." if improved and not timely else None),
        "training_period": [date(first), date(last)],
        "first_validation_training_period": [date(first), date(start_test - 1)],
        "validation_period": [date(start_test), date(last)],
        "model_mae": model_mae, "baseline_mae": baseline_mae,
        "validation_months": len(test_months),
        "method": "Climatología mensual + anomalía del mes anterior; validación expansiva",
    }
