# Inventario F1 (J1.1) — actualizado 2026-11-14

Base: `origin/main` en `4343014` (PR #1–#4 mergeados) + rama `feat/jacky-f1-contracts-complete`. Ramas remotas sin mergear: `emanuel/fase1-decisiones-fixtures`, `docs/narrativa-y-borradores`, `docs/plan-detective-tico`. La versión anterior de este archivo (solo README en el repo) quedó obsoleta.

## Estado por módulo
| Módulo | Dueño | Estado | Evidencia |
|---|---|---|---|
| `src/contracts.py` | Jacky | Contratos v2 completos de §4 salvo `EvidenceCard` tipado (la ficha es `dict`) | 14 tests |
| `src/service_mock.py` | Jacky | 9 de 10 firmas; `get_event_view` (P1) pendiente | 14 tests |
| `src/service.py` real | Jacky | **No existe** (F2/F3) | — |
| `src/ingest.py`, `src/regions.py`, `scripts/build_data.py`, `data/` | Samuel | En main: parquet + raw NASA POWER, máscara `cr-land-mask-v2.0` | `tests/test_data_qc.py` (no ejecutable aquí: falta numpy/pandas) |
| `app.py` | Kevin | En main; consume `service_mock` con selector `HEFESTO_USE_MOCK` | no ejecutada aquí (streamlit no verificado) |
| `config/discovery.json` | Joshua | En main; lo lee `recommend_variable` | test |
| `src/statistics.py`, `src/prepare.py` | Emanuel | **No en main**; fixtures en `emanuel/fase1-decisiones-fixtures` | — |
| `export.py`, ficha serializada | Kevin | No existe; `ExportBundle` es solo el tipo | — |

## Diferencias con v2 aún abiertas
- Mock usa `mask_version="mock"`; los datos reales usan `cr-land-mask-v2.0`. Se mantiene a propósito (synthetic); el servicio real debe tomar el de `regions.py`.
- Celdas del mock duplicadas a mano de `regions.VERIFIED_LAND_CELLS`; un test las compara cuando pandas está instalado.
- No hay adaptador v1→v2: no existen consumidores v1.
- Pronóstico, agua y cobertura de servicio: fuera del plan v2; ver `F1_ESPEC_CONSULTA.md`.

## Bloqueos / no verificado
- Unidad mensual `mm/day`, cobertura 1981–2024: Samuel debe confirmar contra el raw ya descargado.
- se/p/IC del mock son marcadores, no HAC. La ciencia real depende de `statistics.py` (Emanuel).
- No se ejecutó la app Streamlit ni `test_data_qc.py` en este entorno.
