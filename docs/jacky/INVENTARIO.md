# Inventario F1 (JACKY-01) — 2026-11-14

Rama de trabajo: `feat/jacky-contracts-v2` (desde `main`, árbol limpio, sin push). "No encontrado localmente" no implica inexistente en otras ramas: solo existe `origin/main` con un commit (`afb219e`).

## Implementado (antes de F1)
- Solo `README.md` (título). Sin código, tests, dependencias ni config.

## No encontrado localmente
- `AGENTS.md`, `CLAUDE.md`, `docs/claude-code-jacky/00_LEEME_JACKY.md`, `docs/claude-code-jacky/REFERENCIA_PLAN_HEFESTO_V2.md`, `docs/jacky/ESTADO.md`, `docs/decisions.md`, `AI_USAGE.md`.
- Contrato v1, IDN/EEP, caché, datos, máscaras: nada. No hay consumidores v1 → **no se creó adaptador v1→v2 ni migración** (se evita fabricarla).

## Fuente usada para contratos
`C:\Users\jacky\Downloads\Hefesto_Plan_y_Prompts_v2\PLAN-HEFESTO.md` §4 (fuera del repo). `Downloads\PLAN-HEFESTO.md` difiere de él y no se comparó.

## Comparación v1→v2 (según plan §0; v1 no verificable en código)
| Tema | v2 en F1 |
|---|---|
| Regiones | CR_PN/CR_CAR; IDN/EEP no existen, quedan P1 opcional |
| TrendResult | +`p_adjusted`, `family_id`, `significant`; 23 campos obligatorios |
| Niveles | none (n<10) / descriptive (10–29) / inferential (≥30) |
| Familias | BY regional 2 variables × 2 regiones; metadatos de familia |
| Ficha | no implementada (F2) |

## Contratos y consumidores
| Contrato | Archivo | Consumidores |
|---|---|---|
| VariableInfo, RegionSpec, QueryParams, TrendResult, `validate_query`, `to_json` | `src/contracts.py` | Emanuel (statistics), Samuel (regions/ingest), Kevin (UI/export) |
| Firmas servicio mock | `src/service_mock.py` | Kevin, Emanuel |

Firmas F1 en mock: `list_variables`, `list_regions`, `get_coverage`, `get_annual_series`, `get_trend`, `get_comparison`.
**Pendientes (lanzan NotImplementedError):** `get_cell_trends`, `get_event_view` (P1), `build_provenance`, `build_evidence_card`. Faltan además `recommend_variable` (Joshua/Kevin), `CellTrends`, `RegionalMonthly`/`RegionalAnnual` como tipos, `ExportBundle`, y el servicio real `src/service.py` (F2). Contrato completo **no** cerrado.

## Pruebas disponibles
`python -m unittest discover -s tests -t .` → 8 tests OK (Python 3.15.2). `pytest` no instalado; se usó `unittest` (stdlib). Sin dependencias de terceros en F1.

## Bloqueos / no verificado
- Unidad mensual PRECTOTCORR `mm/day`, cobertura 1981–2024, bbox y malla: [verificar] con muestra real (Samuel).
- Fixtures científicas de Emanuel: pendientes. Mock usa valores sintéticos; `se/p/IC` en nivel inferential son **marcadores**, no HAC real (warning `mock_inference_placeholder`).
- Sin statsmodels/pandas en entorno: no verificado.

## Quién entrega qué para v2 completo
Emanuel: fixtures + `statistics.py` (HAC/BY). Samuel: ingesta, máscaras, muestra. Kevin: UI/export/serialización ficha. Joshua: `config/discovery.json`. Jacky: F2 firmas restantes, `service.py`. Revisión: este PR requiere revisión ajena (no autoaprobar).
