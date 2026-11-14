# F2 Componentes — Resumen ejecutivo (Jacky)

Fecha: 14 de noviembre de 2026. Rama `feat/jacky-f2-componentes` (sobre F1), sin commit ni push.

## En una frase

El mock completo y la especificación de adaptadores de F2 están listos. Cubren los seis estados de disponibilidad, los cinco productos (histórico, evento, pronóstico, agua y cobertura del servicio), la caché con snapshots y el export para Kevin. Todo es sintético y las firmas siguen siendo **[PROPUESTA]**: nada se ha acordado con los compañeros ni existe servicio real.

## Qué se entregó

| ID | Entregable | Dónde | Estado |
|---|---|---|---|
| J2.1 | Mock con 6 estados (`available`, `partial`, `unavailable`, `unsupported`, `stale`, `error`) | `src/service_mock_f2.py`, `src/contracts_ext.py` | Hecho |
| J2.2 | Especificación de adaptadores, errores esperados y caché | `docs/jacky/F2_ESPEC_ADAPTADORES.md` | Hecho |
| J2.3 | Catálogo y consultas: `list_zones`, `list_cells`, `get_capabilities`, `get_data_coverage`, `get_series`, `get_map`, `get_event_series` | `src/service_mock_f2.py` | Hecho |
| J2.4 | `get_local_forecast`, `get_water_distribution`, `get_service_coverage` | `src/service_mock_f2.py` | Hecho |
| J2.5 | Clave de caché, matriz de invalidación, store y snapshots en disco | `src/snapshots.py` | Hecho |
| J2.6 | Ficha, CSV y JSON; 14 ejemplos reproducibles | `src/export_f2.py`, `scripts/build_examples_f2.py`, `docs/jacky/examples/` | Hecho |

Verificación: 97 tests OK con `.venv` (`python -m unittest discover -s tests -t .`). Los ejemplos se generan idénticos en dos corridas seguidas.

## Cómo queda cada producto

| Producto | Disponible | Se degrada con razón explícita |
|---|---|---|
| Histórico (serie mensual/anual, mapa por celda) | CR_PN, CR_CAR | zona sin datos, ventana truncada, snapshot vencido, resolución diaria, fallo técnico |
| Episodio El Niño 1997-98 | anomalía con baseline 1981–2010 | baseline corto → anomalía null y `partial` |
| Pronóstico | CR_PN (validado) | no evaluado, validación fallida, sin modelo, vencido; la metadata siempre viaja |
| Distribución de agua | CR_PN, CR_CAR (ene–jun 2024) | sin registros, ventana fuera de rango |
| Cobertura del servicio | indicadores con denominador | CR_CAR sin denominador → `value` null y `partial` |

## Decisiones clave (detalle en `docs/decisions.md`, D13–D27)

- Los contratos v2 no cambian. Los tipos nuevos van aparte (`2.1-proposal`).
- Falta de datos en una consulta válida es `availability`, no excepción ni cero. Una consulta mal formada lanza `ValueError`.
- Un pronóstico no validado nunca se presenta como predicción. No se extrapola la tendencia histórica.
- Las correcciones de agua son registros versionados. Pausa registrada, cero y sin reporte son estados distintos.
- Porcentajes con denominador ausente son null. Valores >100 % se conservan con flag. No se promedia entre zonas.
- La clave de caché lleva `source_mode`, por lo que mock y real no comparten entradas. `generated_at`, `checked_at` y la hipótesis no son identidad. La frescura se reevalúa al leer.
- Sin datos no hay CSV vacío: la ausencia va en `manifest.json` con su razón.

## Límites que conviene tener presentes

- Todo es sintético y `se/p/IC` del mock son marcadores, no un ajuste real.
- No existe `src/service.py`. Que el servicio real nunca caiga a mock en silencio (D6) está definido pero **no verificado**.
- `get_event_view` (P1 de F1) sigue sin implementar.
- Los CSV llevan `result_id` y claves de unión, no columnas de procedencia ni escala. Esos datos viven en `evidence.json`/`provenance.json` del mismo export. Falta confirmar con Kevin si lo quiere así.
- Los datos reales procesados (`data/processed`) solo cubren POWER histórico. No hay pronóstico ni registros de agua reales.
- Streamlit no se ejecutó en este entorno. No hay URL ni respaldo local probados (F4/F5).

## Criterios de aceptación de F2

| Criterio | Evidencia | Estado |
|---|---|---|
| Mock y real comparten firmas y forma | Mock completo; real inexistente | Parcial: falta el real (F3) |
| Kevin diseña pantallas y export sin inventar campos | 14 ejemplos cubren los 6 estados y los 5 productos | Listo para su revisión |
| No se confunden sintético, histórico, pronóstico y agua | `product`, `source_mode`, `synthetic` y `availability` en cada respuesta; la ficha muestra la etiqueta | Cumplido en mock (con tests) |
| Matriz de invalidación cubre zonas, datos, método, modelo y denominadores | `INVALIDATION_MATRIX`, probada cambio por cambio | Cumplido |
| Sin fallback silencioso a mock ni ciencia recalculada en la UI | El export solo serializa; no hay real que probar | Parcial |
| Salidas con procedencia, escala, períodos efectivos y disponibilidad hasta CSV/JSON | Presentes en JSON y manifest; el CSV los enlaza por `result_id` | Cumplido con la salvedad anterior |

## Acuerdos pendientes por compañero

| Con | Pendiente | Ref. |
|---|---|---|
| Samuel | IDs y geometría de celda, deduplicación del mapa; registros de agua (unidad, granularidad, correcciones), crosswalk y denominador de hogares | Q1, Q7 |
| Emanuel | Familia para zonas nuevas, tolerancias; target, horizonte y validación del pronóstico; `degenerate_series` y `coverage_fraction` | Q3, Q4, Q6 |
| Kevin | Funciones internas o bundle JSON; forma de `QueryParams.regions` frente a `zone_ids`; metadata visible; formato de export | Q2, Q5, Q8, Q9 |
| Joshua | Textos de ausencia y opciones soportadas por producto | — |
| Diego | Matriz de casos contractuales a partir de los ejemplos; qué productos entran a la demo real | — |

## Borradores de handoff (preparados, no enviados)

**Kevin:** "Los ejemplos de `docs/jacky/examples/` muestran cada producto y estado con su export completo. Cada respuesta trae `availability.status` y `reason_code` para decidir qué habilitar y qué texto mostrar. Dime si consumes funciones o un bundle, y si los CSV necesitan columnas de procedencia."

**Emanuel y Samuel:** "`F2_ESPEC_ADAPTADORES.md` lista lo que el servicio real necesita de ustedes y los errores esperados. Emanuel: target, horizonte, validación y formato del pronóstico. Samuel: registros de agua versionados, crosswalk y denominador de hogares."

**Joshua:** "Cada producto puede devolver `partial`, `unavailable`, `unsupported`, `stale` o `error`, con una razón. Necesito tus textos para esos casos; los códigos están en la especificación."

**Diego:** "Los 14 casos de `docs/jacky/examples/` pueden ser la base de la matriz contractual. Falta definir qué productos entran a la demo real."

## Siguiente paso recomendado

1. Revisar el PR de F2 junto con F1 y confirmar con Kevin el formato de export.
2. Cerrar las preguntas Q6 y Q7 con Emanuel y Samuel, que bloquean el pronóstico y el agua reales.
3. F3: crear `src/service.py` con las mismas firmas, que falle de forma explícita si falta una dependencia, y correr contra él los mismos tests y ejemplos.
