"""Read-only data adapter for the Detective Tico web interface."""
from functools import lru_cache
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from tempfile import NamedTemporaryFile

from .contracts import COVERAGE_END_YEAR, COVERAGE_START_YEAR, REGION_IDS, VARIABLE_IDS, to_json, to_jsonable, validate_query
from .enso import episode_comparison
from .evidence import evidence_family
from .ingest import parse_monthly_records
from .prepare import build_regional_annual, prepare_regional_series
from .regions import REGION_SPECS, mask_records
from .statistics import compare_historical_windows

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web" / "public" / "data"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def climate_package():
    provenance = read_json(ROOT / "data" / "processed" / "provenance_base.json")
    masks = mask_records()
    raw_rows = []
    for variable in VARIABLE_IDS:
        name = f"data/raw/nasa_power_monthly_{variable}_{COVERAGE_START_YEAR}_{COVERAGE_END_YEAR}.json"
        raw = (ROOT / name).read_bytes()
        expected = next(record["sha256"] for record in provenance["raw_files"] if record["path"] == name)
        if sha256(raw).hexdigest() != expected:
            raise ValueError(f"Huella SHA-256 inesperada en {name}")
        payload = json.loads(raw)
        expected_unit = "C" if variable == "T2M" else "mm/day"
        if payload["parameters"][variable]["units"] != expected_unit:
            raise ValueError(f"Unidad de origen inesperada en {name}")
        raw_rows.extend(parse_monthly_records(payload, variable))
    prepared = prepare_regional_series(raw_rows, masks)
    by_cell = defaultdict(list)
    for row in raw_rows:
        key = row["region_id"], row["lat"], row["lon"]
        by_cell[key].append(dict(row, coverage_fraction=float(row["value"] is not None)))

    cells = {}
    for mask in masks:
        region, lat, lon = mask["region_id"], mask["lat"], mask["lon"]
        cell_id = f"POWER:{lat:g}:{lon:g}"
        if cell_id in cells:
            cells[cell_id]["regions"].append(region)
            continue
        monthly = by_cell[region, lat, lon]
        cells[cell_id] = {
            "id": cell_id, "region": region, "regions": [region], "lat": lat, "lon": lon,
            "bbox": [lon - .3125, lat - .25, lon + .3125, lat + .25],
            "monthly": monthly, "weight": mask["weight"],
            "annual": build_regional_annual(monthly, regions=(region,)),
        }
    return prepared, cells, provenance


def annual_rows():
    return climate_package()[0]["regional_annual"]


@lru_cache(maxsize=48)
def _evidence(start, end, variable=None):
    prepared, cells, _ = climate_package()
    if variable is None:
        series = {region: (region, prepared["regional_annual"]) for region in REGION_IDS}
        return evidence_family(series, start, end, "regions")
    series = {key: (cell["region"], cell["annual"]) for key, cell in cells.items()}
    return evidence_family(series, start, end, "cells", variable)


def climate(region, variable, start=COVERAGE_START_YEAR, end=COVERAGE_END_YEAR,
            *, window_a=None, window_b=None, cell_id=None):
    validate_query(variable, region, start, end)
    if region not in REGION_IDS:
        raise ValueError("La consulta requiere una zona climática")
    prepared, cells, provenance = climate_package()
    if cell_id is not None and (cell_id not in cells or region not in cells[cell_id]["regions"]):
        raise ValueError("La celda elegida no pertenece a la zona")
    selected_cell = cells.get(cell_id)
    rows = selected_cell["annual"] if selected_cell else prepared["regional_annual"]
    subject_region = selected_cell["region"] if selected_cell else region
    spec = REGION_SPECS[region]
    series = [r for r in rows if r["region_id"] == subject_region and r["variable"] == variable
              and start <= r["year"] <= end]
    comparison = None
    if end > start or window_a is not None or window_b is not None:
        comparison = compare_historical_windows(
            rows, variable=variable, region_id=subject_region, window_a=window_a, window_b=window_b,
            coverage_start_year=start, coverage_end_year=end,
        )
    regional, regional_families = _evidence(start, end)
    grid, grid_families = _evidence(start, end, variable)
    evidence = grid[cell_id, variable] if cell_id else regional[region, variable]
    mk = evidence["mann_kendall"]
    trend = evidence["ols"]
    catalog = read_json(ROOT / "data" / "web" / "enso.json")

    def event(monthly, owner):
        return episode_comparison([row for row in monthly if row["region_id"] == owner],
                                  variable, catalog, COVERAGE_START_YEAR, COVERAGE_END_YEAR)

    grid_view = []
    for key, cell in cells.items():
        if region not in cell["regions"]:
            continue
        cell_view = {field: cell[field] for field in ("id", "lat", "lon", "bbox", "weight")}
        if comparison:
            matching = compare_historical_windows(
                cell["annual"], variable=variable, region_id=cell["region"],
                window_a=(comparison.window_a.start_year, comparison.window_a.end_year),
                window_b=(comparison.window_b.start_year, comparison.window_b.end_year),
                coverage_start_year=start, coverage_end_year=end,
            )
            cell_view.update(window_a_mean=matching.window_a.mean, window_b_mean=matching.window_b.mean)
        anomaly = event(cell["monthly"], cell["region"])
        months = anomaly["months"]
        differences = [month["anomaly"] for month in months]
        neutral_differences = [month["vs_neutral"] for month in months]
        cell_view["enso_mean_anomaly"] = mean(differences) if differences and None not in differences else None
        cell_view["enso_mean_vs_neutral"] = (
            mean(neutral_differences) if neutral_differences and None not in neutral_differences else None
        )
        cell_view["evidence"] = grid[key, variable]
        cell_view["long_term_slope"] = grid[key, variable]["ols"].slope_per_decade
        cell_view["significant"] = grid[key, variable]["ols"].significant
        grid_view.append(cell_view)

    monthly = selected_cell["monthly"] if selected_cell else prepared["regional_monthly"]
    return to_jsonable({
        "schema_version": "2.0",
        "regionId": region,
        "cellId": cell_id,
        "bbox": spec.bbox,
        "variable": variable,
        "source": "NASA POWER · MERRA-2",
        "sourceUrl": "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/",
        "synthetic": False,
        "series": series,
        "trend": trend,
        "evidence": evidence,
        "methods_disagree": (trend.significant != mk["significant"]
                             if trend.significant is not None and mk["significant"] is not None else None),
        "families": {"regions": regional_families, "cells": grid_families},
        "comparison": comparison,
        "enso": event(monthly, subject_region),
        "cells": grid_view,
        "provenance": provenance,
        "limitations": [
            spec.scale_warning,
            "Coincidencia con El Niño: comparación descriptiva sin atribución causal.",
            "La precipitación no mide caudal ni continuidad del servicio de agua.",
            "La cobertura de tendencia expresa la fracción de años completos de la ventana.",
        ],
        "forecast": forecast_status(region, variable),
    })


def local_catalog():
    base = ROOT / "data" / "web"
    catalog = read_json(base / "local.json")
    cantons = read_json(base / "cantons.json")
    return dict(catalog, cantons=cantons["cantons"], canton_source=cantons["source"])


def forecast_status(region, variable):
    from .forecast import evaluate_station

    station_file = ROOT / "data" / "local" / f"{region}_{variable}.json"
    if station_file.is_file():
        try:
            station = read_json(station_file)
            return evaluate_station(station["records"], station["metadata"], variable)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return {"status": "station_data_invalid", "message": f"Datos de estación inválidos: {error}"}
    return {"status": "local_data_pending", "message": "Pronóstico pendiente de datos locales de estación.",
            "source_url": "https://imn.ac.cr/solicitud-de-servicios"}


def export_snapshot():
    from .export import evidence_card

    snapshot = {
        "climate": {region: {variable: evidence_card(region, variable) for variable in VARIABLE_IDS}
                    for region in REGION_IDS},
        "cells": {
            region: {
                cell["id"]: {variable: evidence_card(region, variable, cell_id=cell["id"])
                             for variable in VARIABLE_IDS}
                for cell in climate_package()[1].values() if region in cell["regions"]
            }
            for region in REGION_IDS
        },
        "local": local_catalog(),
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    target = PUBLIC / "snapshot.json"
    content = to_json(snapshot, separators=(",", ":"))
    with NamedTemporaryFile(dir=PUBLIC, mode="w", encoding="utf-8", delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(content)
            output.close()
            temporary.replace(target)
        finally:
            output.close()
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    export_snapshot()
