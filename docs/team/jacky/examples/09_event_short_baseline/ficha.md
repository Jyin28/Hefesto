# Ficha de evidencia: event

- Resultado: `28829120ec51d0376b8b2606cc8f775a`
- Estado: **partial** (baseline_insufficient)
- Origen: `mock`, sintetico: `True`, presentable como real: `False`
- Generada: 2026-11-14T00:00:00Z

## Resumen

Episodio EL_NINO_1997_98 1997-06-01..1998-05-31: 12 meses; anomalia no disponible (baseline insuficiente). Descriptivo. Cobertura parcial: Baseline 1981-1990 con 10 valores por mes (<24): anomalia no disponible. Datos sinteticos de contrato (mock): no son evidencia cientifica.

## Consulta

```json
{
  "product": "event",
  "variable": "PRECTOTCORR",
  "zone_ids": [
    "CR_PN"
  ],
  "cell_ids": [],
  "spatial_level": "zone",
  "start_date": "1997-06-01",
  "end_date": "1998-05-31",
  "time_resolution": "annual",
  "preset_id": null,
  "event_id": "EL_NINO_1997_98",
  "baseline": "1981-1990",
  "analysis_scope_id": null,
  "metric": null
}
```

Ventana efectiva: 1997-06-01..1998-05-31

## Advertencias

- baseline_insufficient
- synthetic

## Limitaciones

- Datos sinteticos de contrato; no son evidencia cientifica.
- Celdas de decenas de km (0,5 x 0,625 grados); no es limite administrativo ni detalle de finca.

data_sha256: `85b8f56ee6c0bb625154829a477f1c220b1d18e163aa4d6ee1f0cc9531883cd1`  
analysis_version: `2.0`
