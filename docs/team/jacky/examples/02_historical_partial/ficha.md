# Ficha de evidencia: historical

- Resultado: `7e5ffaee2becfec5d2effb94620ca21c`
- Estado: **partial** (window_truncated)
- Origen: `mock`, sintetico: `True`, presentable como real: `False`
- Generada: 2026-11-14T00:00:00Z

## Resumen

Serie T2M annual 1981-01-01..2010-12-31: 30 registros. Cobertura parcial: Cobertura parcial: efectivo 1981-01-01..2010-12-31; faltan parte de la ventana. Datos sinteticos de contrato (mock): no son evidencia cientifica.

## Consulta

```json
{
  "product": "historical",
  "variable": "T2M",
  "zone_ids": [
    "MOCK_PARTIAL"
  ],
  "cell_ids": [],
  "spatial_level": "zone",
  "start_date": "1981-01-01",
  "end_date": "2024-12-31",
  "time_resolution": "annual",
  "preset_id": null,
  "event_id": null,
  "baseline": null,
  "analysis_scope_id": null,
  "metric": null
}
```

Ventana efectiva: 1981-01-01..2010-12-31

## Advertencias

- synthetic

## Limitaciones

- Datos sinteticos de contrato; no son evidencia cientifica.
- Celdas de decenas de km (0,5 x 0,625 grados); no es limite administrativo ni detalle de finca.

data_sha256: `41e62f50e1d07bd1562792545c9f8e858820d77f523a0168375834395244daf2`  
analysis_version: `2.0`
