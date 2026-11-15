# Ficha de evidencia: forecast

- Resultado: `b89274fb3d310e4986f08ce038268173`
- Estado: **available**
- Origen: `mock`, sintetico: `True`, presentable como real: `False`
- Generada: 2026-11-14T00:00:00Z

## Resumen

Pronostico T2M zona CR_PN: 6 puntos 2025-01-01..2025-06-30; validacion validated. Datos sinteticos de contrato (mock): no son evidencia cientifica.

## Consulta

```json
{
  "product": "forecast",
  "variable": "T2M",
  "zone_ids": [
    "CR_PN"
  ],
  "cell_ids": [],
  "spatial_level": "zone",
  "start_date": "2025-01-01",
  "end_date": "2025-06-30",
  "time_resolution": "annual",
  "preset_id": null,
  "event_id": null,
  "baseline": null,
  "analysis_scope_id": null,
  "metric": null
}
```

Ventana efectiva: 2025-01-01..2025-06-30

## Advertencias

- synthetic

## Limitaciones

- Datos sinteticos de contrato; no son evidencia cientifica.
- Celdas de decenas de km (0,5 x 0,625 grados); no es limite administrativo ni detalle de finca.

data_sha256: `652aff1544af752e9f3e62ab45209f84f9a0ca379fa3ac8d6d8ca6371d6ffd65`  
analysis_version: `2.0`
