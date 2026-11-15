"""Construye los datasets mock y reales de Costa Rica y ejecuta QC (AguaAlerta v2).

Propietario: Samuel.
Uso: python -m scripts.build_data
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from src.contracts import COVERAGE_END_YEAR, COVERAGE_START_YEAR, MONTHLY_UNITS, to_json
from src.ingest import ingest_all
from src.regions import MASK_SOURCE, MASK_VERSION, REGION_SPECS, VERIFIED_LAND_CELLS, build_masks_df


def build_mock_grid(output_path: Path) -> pd.DataFrame:
    """Genera data/mock/mock_grid.parquet con geometria real CR y tendencias conocidas."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dates = pd.date_range(f"{COVERAGE_START_YEAR}-01-01", f"{COVERAGE_END_YEAR}-12-01", freq="MS")
    rng = np.random.default_rng(42)
    rows = []

    for region_id, coords in VERIFIED_LAND_CELLS.items():
        for lat, lon in coords:
            for idx, ts in enumerate(dates):
                years_elapsed = idx / 12.0
                seasonal = np.sin(2 * np.pi * (ts.month - 1) / 12.0)

                # T2M sintetico: +0.25 degC/decada en CR_PN, +0.15 degC/decada en CR_CAR
                t_slope = 0.025 if region_id == "CR_PN" else 0.015
                t_val = 26.5 + 1.2 * seasonal + t_slope * years_elapsed + rng.normal(0, 0.25)
                rows.append(
                    {
                        "region_id": region_id,
                        "variable": "T2M",
                        "lat": lat,
                        "lon": lon,
                        "time": ts,
                        "value": round(float(t_val), 3),
                        "unit": MONTHLY_UNITS["T2M"],
                        "synthetic": True,
                    }
                )

                # PRECTOTCORR sintetico (mm/day): ciclo estacional marcado, tendencia leve
                p_slope = -0.01 if region_id == "CR_PN" else 0.015
                p_val = max(0.0, 6.0 + 4.5 * seasonal + p_slope * years_elapsed + rng.normal(0, 1.1))
                rows.append(
                    {
                        "region_id": region_id,
                        "variable": "PRECTOTCORR",
                        "lat": lat,
                        "lon": lon,
                        "time": ts,
                        "value": round(float(p_val), 3),
                        "unit": MONTHLY_UNITS["PRECTOTCORR"],
                        "synthetic": True,
                    }
                )

    df = pd.DataFrame(rows).astype(
        {
            "region_id": "string",
            "variable": "string",
            "lat": "float64",
            "lon": "float64",
            "time": "datetime64[ns]",
            "value": "float64",
            "unit": "string",
            "synthetic": "bool",
        }
    )
    df.to_parquet(output_path, index=False)
    return df


def run_qc(grid_df: pd.DataFrame, masks_df: pd.DataFrame, processed_dir: Path) -> None:
    """Ejecuta verificaciones obligatorias de calidad antes de entregar al equipo."""
    key_cols = ["region_id", "variable", "lat", "lon", "time"]
    dups = int(grid_df.duplicated(subset=key_cols).sum())
    assert dups == 0, f"QC FALLO: Hay {dups} claves duplicadas."
    assert not grid_df["synthetic"].any(), "QC FALLO: Hay filas sinteticas en processed."
    assert grid_df["time"].dt.month.between(1, 12).all(), "QC FALLO: Mes fuera de 1..12."

    for region_id, grp in masks_df.groupby("region_id"):
        w_sum = float(grp["weight"].sum())
        assert np.isclose(w_sum, 1.0, atol=1e-6), f"QC FALLO: Pesos en {region_id} suman {w_sum}."
        assert len(grp) >= 2, f"QC FALLO: {region_id} tiene menos de 2 celdas."

    total_bytes = sum(f.stat().st_size for f in processed_dir.glob("*") if f.is_file())
    total_mb = total_bytes / (1024 * 1024)
    assert total_mb < 20.0, f"QC FALLO: Cache supera 20 MB ({total_mb:.2f} MB)."

    print("\n=== REPORTE DE CONTROL DE CALIDAD (QC) ===")
    print(f"Filas totales reales: {len(grid_df):,}")
    print(f"Celdas activas por sector: {masks_df.groupby('region_id').size().to_dict()}")
    print(f"Rango temporal: {grid_df['time'].min().date()} a {grid_df['time'].max().date()}")
    for var, grp in grid_df.groupby("variable"):
        nans = int(grp["value"].isna().sum())
        print(
            f"  - {var} ({grp['unit'].iloc[0]}): "
            f"min={grp['value'].min():.2f}, max={grp['value'].max():.2f}, NaNs={nans}"
        )
    print(f"Peso total en disco (data/processed): {total_mb:.3f} MB (< 20 MB OK)")
    print("Estado QC: APROBADO\n")


def write_data_sources_md(path: Path, provenance: dict) -> None:
    """Documenta fuentes, licencias y limitaciones para Joshua y Diego."""
    content = f"""# Fuentes de Datos y Limitaciones Espaciales — AguaAlerta v2

## 1. Fuente primaria (S1 / S2)
* **Proveedor:** {provenance['provider']}
* **Endpoint:** NASA POWER Monthly and Annual Regional API (`{provenance['api_version']}`)
* **Documentacion oficial:** {provenance['source_page']}
* **Variables:**
  * `T2M`: Temperatura del aire a 2 metros (`degC` mensual; media anual ponderada por dias en `degC`).
  * `PRECTOTCORR`: Precipitacion corregida (`mm/day` mensual; acumulado anual en `mm/yr`).
* **Cobertura temporal:** {COVERAGE_START_YEAR}-01 a {COVERAGE_END_YEAR}-12 (528 meses por celda).
* **Fecha de extraccion (UTC):** `{provenance['retrieved_at']}`
* **Licencia:** Datos abiertos de acceso publico NASA POWER (sin autenticacion Earthdata requerida).

## 2. Mascara geografica y sectores de Costa Rica (`{MASK_VERSION}`)
* **Fuente de mascara:** {MASK_SOURCE}
* **Resolucion nativa:** `0.5 deg latitud x 0.625 deg longitud` (~55 km x 69 km en Costa Rica).
* **Sectores:**
  * `CR_PN` — {REGION_SPECS['CR_PN'].name}: bbox `{list(REGION_SPECS['CR_PN'].bbox)}` (5 celdas terrestres).
  * `CR_CAR` — {REGION_SPECS['CR_CAR'].name}: bbox `{list(REGION_SPECS['CR_CAR'].bbox)}` (5 celdas terrestres).
* **Ponderacion espacial:** Promedio ponderado por `cos(lat)` normalizado por sector.

## 3. Limitaciones cientificas obligatorias
1. **Reanalisis, no estaciones locales:** NASA POWER entrega estimaciones de modelo atmosferico con asimilacion de observaciones (MERRA-2), no mediciones directas de pluviometros o termometros locales.
2. **Escala regional:** Cada celda cubre decenas de kilometros; no representa fincas, cantones ni cuencas especificas.
3. **Mezcla costera y orografia:** Las celdas costeras incluyen fraccion oceanica y suavizan gradientes abruptos de las cordilleras de Costa Rica.
4. **Uso educativo:** Herramienta de exploracion historica; no pronostica sequias, inundaciones ni disponibilidad de agua potable.
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    mock_dir = root / "data" / "mock"
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("1/4 Generando mock_grid.parquet (synthetic=True)...")
    build_mock_grid(mock_dir / "mock_grid.parquet")

    print("2/4 Construyendo masks.parquet...")
    masks_df = build_masks_df()
    masks_df.to_parquet(processed_dir / "masks.parquet", index=False)

    print("3/4 Descargando y limpiando datos reales NASA POWER (1981-2024)...")
    grid_df, provenance = ingest_all(raw_dir)
    grid_df.to_parquet(processed_dir / "grid_monthly.parquet", index=False)

    prov_path = processed_dir / "provenance_base.json"
    prov_path.write_text(to_json(provenance, indent=2), encoding="utf-8")

    print("4/4 Ejecutando QC y generando docs/DATA_SOURCES.md...")
    run_qc(grid_df, masks_df, processed_dir)
    write_data_sources_md(root / "docs" / "DATA_SOURCES.md", provenance)


if __name__ == "__main__":
    main()