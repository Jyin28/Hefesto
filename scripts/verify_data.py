"""Verifica que TODOS los datos que usa el producto sean accesibles y consistentes.

Uso:  python scripts/verify_data.py        (código de salida != 0 si algo falla)

Comprueba: huellas SHA-256 de los JSON crudos, esquema/dtypes de grid_monthly.parquet y masks.parquet,
clave única, unidades, celdas verificadas, 528 meses por celda, ausencia de NaN/fill values, pesos de
máscara, coincidencia Parquet == JSON crudo, y que el pipeline anual/estadístico se ejecute.
"""
from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.regions import VERIFIED_LAND_CELLS  # noqa: E402

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("  ok  " if condition else " FAIL ") + message)
    if not condition:
        FAILURES.append(message)


def main() -> int:
    prov = json.loads((ROOT / "data/processed/provenance_base.json").read_text(encoding="utf-8"))
    print("1. Archivos crudos y huellas")
    for entry in prov["raw_files"]:
        path = ROOT / entry["path"]
        check(path.is_file() and sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"SHA-256 {entry['path']}")
    check(prov["synthetic"] is False, "provenance_base.json: synthetic = false")

    print("2. grid_monthly.parquet")
    grid = pd.read_parquet(ROOT / "data/processed/grid_monthly.parquet")
    cols = ["region_id", "variable", "lat", "lon", "time", "value", "unit", "synthetic"]
    check(list(grid.columns) == cols, f"columnas {cols}")
    check(str(grid["time"].dtype).startswith("datetime64"), "time es datetime64")
    check(grid["value"].dtype == "float64" and grid["lat"].dtype == "float64", "value/lat/lon float64")
    check(not grid["synthetic"].any(), "ningún registro sintético")
    check(grid["value"].notna().all(), "sin NaN en value")
    check((grid["value"] > -900).all(), "sin fill values (-999)")
    check(not grid.duplicated(["region_id", "variable", "lat", "lon", "time"]).any(), "clave única")
    check(set(grid["variable"]) == {"T2M", "PRECTOTCORR"}, "variables T2M y PRECTOTCORR")
    check(grid.groupby("variable")["unit"].unique().map(list).to_dict() == {"PRECTOTCORR": ["mm/day"], "T2M": ["degC"]},
          "unidades degC y mm/day")
    check((grid["time"].dt.day == 1).all(), "time = primer día del mes")
    for region, cells in VERIFIED_LAND_CELLS.items():
        sub = grid[grid["region_id"] == region]
        found = {(round(a, 4), round(b, 4)) for a, b in sub[["lat", "lon"]].drop_duplicates().itertuples(index=False)}
        check(found == {(round(a, 4), round(b, 4)) for a, b in cells}, f"{region}: celdas == VERIFIED_LAND_CELLS")
        per_cell = sub.groupby(["variable", "lat", "lon"]).size()
        check((per_cell == 528).all(), f"{region}: 528 meses por celda y variable")
    check(grid["time"].min() == pd.Timestamp("1981-01-01") and grid["time"].max() == pd.Timestamp("2024-12-01"),
          "rango 1981-01 a 2024-12")
    print(f"   rango de valores: T2M {grid[grid.variable == 'T2M'].value.min():.1f}–"
          f"{grid[grid.variable == 'T2M'].value.max():.1f} °C; PRECTOTCORR "
          f"{grid[grid.variable == 'PRECTOTCORR'].value.min():.2f}–{grid[grid.variable == 'PRECTOTCORR'].value.max():.2f} mm/día "
          f"({int((grid[grid.variable == 'PRECTOTCORR'].value == 0).sum())} ceros válidos)")

    print("3. masks.parquet")
    masks = pd.read_parquet(ROOT / "data/processed/masks.parquet")
    check(list(masks.columns) == ["region_id", "lat", "lon", "weight", "mask_version"], "columnas de máscara")
    for region, sub in masks.groupby("region_id"):
        check(abs(sub["weight"].sum() - 1.0) < 1e-6, f"{region}: pesos suman 1")
    check(masks["mask_version"].nunique() == 1, "una sola mask_version")

    print("4. Parquet == JSON crudo de NASA POWER")
    for variable in ("T2M", "PRECTOTCORR"):
        raw = json.loads((ROOT / f"data/raw/nasa_power_monthly_{variable}_1981_2024.json").read_text(encoding="utf-8"))
        lookup = {}
        for feature in raw["features"]:
            lon, lat = feature["geometry"]["coordinates"][:2]
            lookup[(round(lat, 4), round(lon, 4))] = feature["properties"]["parameter"][variable]
        sub = grid[grid["variable"] == variable]
        bad = 0
        for row in sub.itertuples(index=False):
            key = f"{row.time.year}{row.time.month:02d}"
            if lookup[(round(row.lat, 4), round(row.lon, 4))][key] != row.value:
                bad += 1
        check(bad == 0, f"{variable}: {len(sub)} registros coinciden con el crudo ({bad} diferencias)")

    print("5. Pipeline anual y estadístico")
    from src import service
    for variable in ("T2M", "PRECTOTCORR"):
        for region in ("CR_PN", "CR_CAR"):
            series = service.get_annual_series(variable, region, 1981, 2024)
            complete = sum(1 for r in series if r["complete"])
            t = service.get_trend(variable, region, 1981, 2024)
            check(complete == 44 and t.level == "inferential" and t.p_value is not None,
                  f"{variable} {region}: 44 años completos, inferencia OLS+HAC válida")
            vals = [r["value"] for r in series]
            print(f"   {variable} {region}: media anual {sum(vals) / len(vals):.1f} {series[0]['unit']}, "
                  f"min {min(vals):.1f}, max {max(vals):.1f}")

    print()
    if FAILURES:
        print(f"FALLÓ la verificación de datos ({len(FAILURES)} problemas).")
        return 1
    print("Datos verificados: accesibles y consistentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
