# Ejemplos F2 para Kevin (J2.6)

Salida del mock sintetico, reproducible con `python scripts/build_examples_f2.py` (relojes fijados a 2026-11-14). Cada carpeta es un export completo: `manifest.json` lista tablas presentes y ausentes; `evidence.json` es la ficha; `ficha.md` es su version legible.

| Caso | Producto | Estado | Razon | Archivos |
|---|---|---|---|---|
| 01_historical_available | historical | available | - | evidence.json, ficha.md, manifest.json, provenance.json, series.csv |
| 02_historical_partial | historical | partial | window_truncated | evidence.json, ficha.md, manifest.json, provenance.json, series.csv |
| 03_historical_unavailable | historical | unavailable | no_data_for_zone | evidence.json, ficha.md, manifest.json |
| 04_historical_error | historical | error | internal_error | evidence.json, ficha.md, manifest.json |
| 05_historical_unsupported | historical | unsupported | resolution_not_supported | evidence.json, ficha.md, manifest.json |
| 06_historical_stale | historical | stale | snapshot_expired | evidence.json, ficha.md, manifest.json, provenance.json, series.csv |
| 07_map_cells | historical | available | - | cells.csv, evidence.json, ficha.md, manifest.json, provenance.json |
| 08_event_available | event | available | - | event_series.csv, evidence.json, ficha.md, manifest.json, provenance.json |
| 09_event_short_baseline | event | partial | baseline_insufficient | event_series.csv, evidence.json, ficha.md, manifest.json, provenance.json |
| 10_forecast_validated | forecast | available | - | evidence.json, ficha.md, forecast.csv, manifest.json, provenance.json |
| 11_forecast_not_validated | forecast | unavailable | forecast_not_validated | evidence.json, ficha.md, manifest.json |
| 12_water_distribution | water_distribution | available | - | evidence.json, ficha.md, manifest.json, provenance.json, water_distribution.csv, water_records.csv |
| 13_service_coverage_partial | service_coverage | partial | denominator_missing | evidence.json, ficha.md, manifest.json, provenance.json, service_coverage.csv |
| 14_capabilities | capabilities | available | - | evidence.json, ficha.md, manifest.json, provenance.json |

Convenciones CSV: UTF-8, coma, punto decimal, ausente = celda vacia, anidados = JSON compacto, booleanos true/false. Cada fila lleva `result_id` y `product` mas su clave de union. Un producto sin datos no genera CSV: aparece en `tables_absent` con su razon.
