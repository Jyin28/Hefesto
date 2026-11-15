# Ficha de evidencia: historical

- Resultado: `a564e08f2c6bd5677d67ea4addaca5c0`
- Estado: **stale** (snapshot_expired)
- Origen: `mock`, sintetico: `True`, presentable como real: `False`
- Generada: 2026-11-14T00:00:00Z

## Resumen

Serie T2M annual 2000-01-01..2009-12-31: 10 registros. Vencido: no tratar como actual. Datos sinteticos de contrato (mock): no son evidencia cientifica.

## Consulta

```json
{
  "product": "historical",
  "variable": "T2M",
  "zone_ids": [
    "MOCK_STALE"
  ],
  "cell_ids": [],
  "spatial_level": "zone",
  "start_date": "2000-01-01",
  "end_date": "2009-12-31",
  "time_resolution": "annual",
  "preset_id": null,
  "event_id": null,
  "baseline": null,
  "analysis_scope_id": null,
  "metric": null
}
```

Ventana efectiva: 2000-01-01..2009-12-31

## Advertencias

- synthetic
- snapshot_expired

## Limitaciones

- Datos sinteticos de contrato; no son evidencia cientifica.
- Celdas de decenas de km (0,5 x 0,625 grados); no es limite administrativo ni detalle de finca.

data_sha256: `b863a8bce56886fdbe46e8cdf6b96f5def46a1dd448403291cad9c0758119466`  
analysis_version: `2.0`
