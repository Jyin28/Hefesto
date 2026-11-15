# AguaAlerta · Estado y validación (rama MVP)

Revisión del 14 de noviembre de 2026. Producto: app Streamlit sobre datos reales NASA POWER (T2M y PRECTOTCORR, CR_PN y CR_CAR, 1981–2024).

## Qué se comprobó (reproducible)

```powershell
.\.venv\Scripts\python.exe scripts\verify_data.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\build_claims.py   # regenera docs/claims.csv
```

| Comprobación | Resultado |
|---|---|
| Huellas SHA-256 de los JSON crudos | coinciden con `provenance_base.json` |
| `grid_monthly.parquet` | 10 560 filas; esquema y dtypes del contrato; clave única; 0 NaN; 0 fill values; unidades degC y mm/day; 33 ceros válidos de lluvia |
| Celdas | 5 + 5 == `VERIFIED_LAND_CELLS`; 528 meses por celda y variable |
| Máscara | pesos suman 1 por sector |
| Parquet vs crudo | 10 560 registros idénticos al JSON de NASA POWER |
| Anualización | 44 años completos por sector y variable; T2M media ponderada por días; lluvia Σ tasa × días (bisiestos reales) |
| OLS + HAC (L=3, Bartlett, corrección de muestra, t) | coincide con `statsmodels` (pendiente, EE, p, IC) en las 4 series reales |
| BY | familia regional de 4 pruebas y familia de 10 celdas por variable, calculadas completas antes de filtrar |
| UI = exportación | `result_id` idéntico en pantalla, Markdown, JSON y CSV (AppTest) |
| Offline | los recorridos corren con conexiones externas bloqueadas |

## Resultados (1981–2024, ver `docs/claims.csv`)

| Sector y variable | Pendiente por década | IC 95 % individual (HAC L=3) | p ajustado BY |
|---|---:|---|---:|
| Pacífico Norte · temperatura | −0,0365 °C | [−0,143, 0,070] | 1,000 |
| Caribe · temperatura | +0,1440 °C | [0,081, 0,207] | 0,000102 |
| Pacífico Norte · lluvia | +401,6 mm/año | [255,2, 548,0] | 1,5·10⁻⁵ |
| Caribe · lluvia | +592,1 mm/año | [366,4, 817,9] | 1,7·10⁻⁵ |

**Advertencia obligatoria sobre lluvia:** la lluvia de reanálisis no está validada con estaciones y su serie anual pasa de ~1 000–1 500 mm a >3 000 mm.
Estas magnitudes son un patrón del producto, no lluvia observada (ver `docs/limitations.md` §9). Temperatura: Caribe muestra evidencia de aumento;
Pacífico Norte no (evidencia insuficiente, no ausencia de cambio).

## Estado por componente

| Componente | Estado |
|---|---|
| Datos y máscaras | verificados (`verify_data.py`) |
| Estadística | cumple §3 del plan: máscara fija ≥80 %, niveles, huecos, HAC, BY, sensibilidad, degenerados; advertencias del contrato (`temporal_gaps`, `degenerate_series`, `coverage_failure`) |
| Diagnóstico de homogeneidad | Pettitt sobre residuos OLS; no detecta un salto único; advertencia de lluvia siempre visible |
| Servicio real | mismas firmas y formas que el mock; `build_provenance` y `build_evidence_card` completos (§4.7) |
| UI | guía de 3 preguntas, 2 recorridos, 4 tarjetas, series, comparación, mapa de celdas, mensual/anomalías, ENOS 1997–98, diagnósticos, límites, descargas |
| Fuera de alcance (no en la app) | pronóstico, agua/ASADAS, cantones, React |

## Pendientes humanos
- Revisión ajena del PR y de la ciencia; probar en una segunda computadora sin internet y medir tiempos.
- Validar la lluvia contra estaciones del IMN; verificar boletines del ENOS 1997–98 y un período neutral de contraste (hoy "sin verificar").
- Confirmar el formato ejecutable aceptado por el jurado; grabar video y capturas desde esta versión.
