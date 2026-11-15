# Hefesto — Detectives de Tendencias de la Tierra: edición Costa Rica
> Versión 2.0 · actualización del 14 de noviembre de 2026 · hora local: America/Costa_Rica.
> Sustituye la planificación de PLAN-HEFESTO.md más reciente. Es un plan de implementación, no evidencia de una aplicación terminada ni de resultados calculados.
> [SUPUESTO]: decisión operativa. [verificar]: pendiente de comprobar. No se ha descargado ni analizado el subconjunto científico durante esta actualización.

## 0. Qué cambia y qué se conserva

Base revisada: PLAN-HEFESTO.md, versión incorporada a la conversación el 14 de noviembre a las 09:40 locales. El nuevo Background, Objectives, Potential Considerations y la transcripción entregados por el equipo son la referencia de alcance. No se recibió URL de la pestaña Resources ni del video: [verificar] recursos adicionales sin inventar enlaces.

| Tema | Decisión actualizada | Motivo y migración |
|---|---|---|
| Público | Estudiantes de colegio/universidad y público con interés científico | Priorizar comprensión y exploración guiada |
| Valor nuevo | “Detective Tico”: tres preguntas, comparación de sectores de Costa Rica y ficha de evidencia reproducible | Convierte la selección de variables en una experiencia de investigación |
| Geografía MVP | CR_PN y CR_CAR; IDN/EEP pasan a demostración opcional o se conservan si ya están implementadas | No descargar cuatro regiones desde cero |
| Variables | Conservar T2M y PRECTOTCORR; catálogo pequeño con definiciones | El reto no exige integrar todas las misiones mencionadas |
| Datos y arquitectura | Conservar Python, Streamlit, Plotly, Parquet y API interna | Evitar reescritura y aprendizaje de otro stack |
| Lluvia anual | Conservar suma de tasa mensual × días → mm/yr | Cambia acumulado anual, no tasa media diaria |
| Estacionalidad | Anual para inferencia; mensual y anomalías para aprender | No presentar ciclos estacionales como tendencias |
| Significancia regional | Añadir p_adjusted, family_id y significant; BY sobre las cuatro pruebas de dos variables × dos regiones por ventana | Mostrar una familia explícita, no cuatro decisiones aisladas sin contexto |
| Mapas | BY por variable y ventana sobre ambas regiones, antes de filtrar la vista | Ocultar una región no modifica la corrección |
| Serie incompleta | No comprimir huecos como si años separados fueran consecutivos para HAC | Si hay huecos internos: pendiente descriptiva, inferencia no disponible |
| HAC | Fijar L=3 con sensibilidad 1/5; use_t=True, corrección de muestra | El borrador anterior decía que una fórmula automática da 3 siempre entre n=30 y 44: eso no es exacto. L=3 aquí es una decisión explícita |
| Ventana corta | Conservar niveles n<10, 10–29, >=30; umbrales del producto | No son una ley estadística universal |
| Episodio ENOS | 1997-06 a 1998-05, descriptivo y opcional | Conservar ventana del plan reciente; no confundir anomalía con tendencia |
| Plan B estadístico | Nunca cambiar a p de OLS independiente y seguir presentándolo como equivalente a HAC | Mantener magnitud descriptiva y explicar por qué no se puede evaluar significancia |
| Regiones grandes | Retirar cajas tropicales enormes de la ruta crítica | Reducir volumen y riesgos de API |
| Tiempo | No reiniciar tareas ya realizadas | Si se empieza después de las 07:00, hacer inventario de 20 min y preservar entregas domingo 13:00/16:00 |
| Innovación adicional | Comparación entre ventanas fijas 1981–2024 y 1991–2024: extra | No afirmar que más años necesariamente generan significancia |

## 1. Resumen del producto
Hefesto ayuda a estudiantes a investigar cambios ambientales con datos NASA.
El usuario elige una pregunta, un sector y un período, y recibe una variable explicada en lenguaje sencillo.
Compara sectores del Pacífico Norte y Caribe de Costa Rica mediante series, mapas y tasas de cambio.
Responde qué cambia, dónde, cuánto y con qué evidencia estadística.
Su “Ficha de detective” conserva hipótesis, resultados, límites y procedencia para repetir la investigación.
Es una herramienta educativa de exploración histórica: no pronostica sequías, inundaciones ni disponibilidad de agua potable.

### Innovación aplicable a Costa Rica: Detective Tico
Experiencia P0, sin LLM ni servicios adicionales:
1. **Pregunta:** “¿Ha cambiado la temperatura?” o “¿Ha cambiado la lluvia anual?”.
2. **Lugar:** sector Pacífico Norte o sector Caribe; el otro se ofrece como comparación.
3. **Tiempo:** período dentro de cobertura; por defecto 1981–2024.
4. Recomendación determinista y explicada: calor → T2M; lluvia → PRECTOTCORR. La persona confirma la selección.
5. Cuatro tarjetas de respuesta y una “Ficha de detective” descargable en JSON/Markdown con hipótesis opcional, resultado calculado, advertencias y fuentes.
6. Dos recorridos guiados por botones o texto local: “Investiga el calor” e “Investiga la lluvia”.

Aplicación propuesta: actividad de aula para colegios y universidades de Costa Rica, y conversación educativa con organizaciones comunitarias. No afirmar que se ha validado con usuarios o que una ASADA utiliza el producto.
La ficha no asigna un puntaje de riesgo ni recomienda racionamiento. No se recopilan nombres, ubicación personal ni información sensible.
La novedad está en conectar pregunta cotidiana, territorio costarricense y trazabilidad científica; no se afirma exclusividad o invención mundial.

## 2. Alcance, datos y definición de terminado

| Área | P0 obligatorio | P1 si el MVP está validado | Fuera de alcance |
|---|---|---|---|
| Descubrimiento | Catálogo de dos variables + guía de tres preguntas | Glosario ampliado | Buscador universal de misiones; agente web autónomo |
| Geografía | Dos sectores CR, máscara fija y celdas nativas visibles | IDN/EEP si ya hay caché válida | Polígonos libres, finca/cantón/cuenca a resolución ficticia |
| Tiempo | Mensual para visualizar; anual para inferencia | Ventanas fijas comparadas y detalle por estación | Tendencias no lineales, cambio de régimen automático |
| Ciencia | OLS+HAC, IC, p, BY, niveles descriptivos | Sen y MK corregido como contraste | Predicción, atribución causal |
| UI | Series, mapas por celda, cuatro tarjetas y limitaciones | Animación mensual | Globo 3D |
| Innovación | Detective Tico + ficha reproducible | Modo aula con instrucciones adicionales | Alertas meteorológicas o recomendaciones operativas |
| Casos | Dos recorridos locales: calor y lluvia | Episodio ENOS 1997–98 | Garantizar signos opuestos o p<0,05 |
| Entrega | Repo, ejecutable, slides, video respaldo | Hosting público | Cuentas de usuarios, pagos |

### Datos y acceso
NASA POWER monthly, T2M y PRECTOTCORR; histórico objetivo 1981-01 a 2024-12 [verificar respuesta]. Ver fuentes S1–S2.
La API mensual pública propuesta no requiere Earthdata Login. Descargas protegidas directas de MERRA-2 y extracciones AppEEARS/Giovanni requieren revisar autenticación Earthdata; no son dependencias del MVP. CMR descubre metadatos, no sustituye datos numéricos. MODIS/OMI/AIRS/GPM/GLDAS son vías de ampliación, no conectores obligatorios.
POWER entrega variables de reanálisis: indicar “estimaciones de modelo con asimilación de observaciones”, no “medición directa de un termómetro satelital”.

- T2M mensual: degC. Anual: media ponderada por días, degC.
- PRECTOTCORR mensual: mm/day [verificar metadatos]. Anual: sum(value × days_in_month), mm/yr.
- No convertir directamente la lluvia en caudal, humedad de suelo, recarga o suministro.
- Resolución meteorológica nativa documentada aproximadamente 0,5° lat × 0,625° lon; escala de decenas de kilómetros. Conservar resolución efectiva del producto, sin interpolación que simule detalle.
- API regional: una variable por petición según documentación; límites espaciales y temporales [verificar]. Solicitar primero un año/caja/parámetro. Dividir por años si necesario. Si devuelve coordenadas remuestreadas, verificar malla nativa antes de contar celdas independientes.
- Descartar registros anuales adicionales (ANN o mes 13 si aparecen); no asumir un único nombre universal. Interpretar fill values según metadatos.
- Presupuesto: <=200 celdas en total, 528 meses, dos variables; caché procesada objetivo <20 MB. Ninguna descarga en la demo.

### Sectores costarricenses propuestos
Cajas [SUPUESTO], WGS84, orden [west,south,east,north]. Son ventanas didácticas, no límites administrativos ni climáticos oficiales.

| id | Nombre | bbox |
|---|---|---|
| CR_PN | Sector Pacífico Norte, entorno regional de Guanacaste | [-86.0, 9.75, -85.0, 11.25] |
| CR_CAR | Sector Caribe, entorno regional de Limón | [-84.0, 9.5, -82.75, 10.75] |

Samuel verifica cada celda y conserva centros terrestres costarricenses en una máscara documentada con costa/frontera local de fuente y licencia verificadas. Una celda con centro terrestre puede incluir mar: registrar esa limitación, no atribuirle precisión costera.
Objetivo >=2 celdas elegibles por sector; si solo hay una válida, mostrar explícitamente “celda representativa”, no promedio regional amplio. No ampliar caja buscando un signo o p favorable.
Para celdas completas regulares, peso normalizado cos(lat). Si se recortan polígonos/celdas, usar área de intersección y versionar la máscara; ese recorte no es obligatorio.
Celdas duplicadas de muestreo se deduplican por identidad nativa.

### Criterios de aceptación del producto
- Las cuatro preguntas se responden en ambas variables; “no evaluable” se admite para entradas insuficientes, pero el demo histórico debe permitir una prueba válida.
- Dos ejemplos locales se reproducen sin red con el mismo resultado.
- p sin ajustar y p ajustado identificados; señal de significancia basada en la familia documentada.
- Nada se presenta como observado si es sintético.
- Mapa y serie muestran sus propios períodos; no usar mapa precalculado de otra ventana sin bloquear/explicar.
- App abre en segunda computadora sin herramientas de desarrollo, con el formato aceptado por el jurado [verificar].

## 3. Arquitectura y método científico

Stack conservado: Python + pandas/NumPy/statsmodels + Streamlit/Plotly; Parquet con pyarrow.
Un proceso y funciones internas reducen integración; datos y geometrías locales permiten demo sin red.
xarray es opcional en la ingesta; congelar dependencias realmente verificadas, no inventar versiones.

Flujo: catálogo/guía → QueryParams → servicio → caché de datos → preparación → estadísticas → UI + ficha/exportación.
Flujo de datos: fuente → raw inmutable → grid_monthly.parquet → máscaras → series regionales/anuales → resultados.
Pruebas y presentación consumen fixtures desde la primera hora.

### Método implementable
1. Máscara elegible fija por consulta: excluir celdas sin los meses necesarios; conservar >=80 % del peso terrestre candidato por sector [SUPUESTO de calidad]. Si no se alcanza, estado insufficient_data; no cambiar pesos mes a mes. Registrar celdas y cobertura.
2. Series anuales: 12 meses válidos; temperatura media ponderada por días; precipitación acumulada anual.
3. Estacionalidad: cada año completo reúne todo el ciclo. La vista mensual opcional de anomalías resta la media del mismo mes en 1981–2010, exigiendo >=24 valores de los 30 años por mes [SUPUESTO].
4. Ajuste y=a+b*(year-first_year). slope_per_decade=10*b; total_change=b*(last_used_year-first_used_year).
5. n<10: sin ajuste. 10–29: magnitud descriptiva. >=30 años consecutivos y ajuste válido: inferencia OLS+HAC, maxlags=3, kernel Bartlett, use_correction=True, use_t=True, prueba bilateral H0:b=0.
6. No comprimir años faltantes. Ante huecos internos, mostrar pendiente con años reales como descriptiva; p/IC inferencial null y warning temporal_gaps.
7. Comprobar escala/unidades de se_hac: error estándar de slope_per_decade; IC en mismas unidades. IC del 95 % individual, no simultáneo.
8. Dos variables × dos sectores por ventana: familia regional de hasta cuatro p válidos, BY a alfa 0,05; registrar planeadas y evaluables. Calcularla completa aunque la UI muestre una sola variable.
9. Mapa: familia BY de todas las celdas elegibles de ambos sectores para una variable/ventana. No filtrar por signo ni por p antes de corregir.
10. Guardar p_value original, p_adjusted o q_value ajustado y tamaño de familia. No p calculable → significant=null, no false.
11. Sensibilidad HAC L=1/5: reportar si cambia la conclusión; nunca escoger el rezago favorable. No incorpora incertidumbre total del reanálisis.
12. FDR no corrige todas las búsquedas hechas durante la sesión: etiquetar exploratorio. Si P1 compara dos ventanas, definir su propia familia antes de mostrarlas, o mostrar solo pendientes descriptivas de comparación.
13. Serie constante/varianza residual cero: resultado degenerado, p/IC null; no p=0. No suavizar/interpolar antes de calcular tendencia.
14. No significativo significa evidencia insuficiente, no “no cambia”. p no es la probabilidad de que H0 sea cierta. Más años pueden cambiar la estimación y no garantizan menor p.
15. El Niño y estacionalidad son procesos distintos de una tendencia lineal multidecadal. Asociación no atribuye causa. Un resultado local puede no reproducir la expectativa regional.

Justificación en una línea: anualización controla composición estacional; OLS mide tasa lineal; HAC considera dependencia temporal de corto alcance; BY considera múltiples pruebas dependientes; sensibilidad expone decisiones frágiles. Fuentes S3–S4.
No se requiere MK para cumplir el reto: el objetivo acepta análisis lineal básico; un segundo método se añade solo después de validar el primero.

## 4. Contratos técnicos v2 — normativos
Propietario: Jacky; revisión Emanuel/Samuel y consumidores. Conservar campos previos cuando sea posible. Versionar schema_version="2.0"; no confundir versionado de datos con versión de API.

### 4.1 Convenciones
- RegionId: CR_PN | CR_CAR en MVP; IDN/EEP solo con preset opcional válido.
- VariableId: T2M | PRECTOTCORR.
- WGS84/EPSG:4326; lat/lon en grados; bbox [west,south,east,north].
- time=datetime64[ns], primer día del mes, etiqueta sin zona; year=int.
- Timestamps de procedencia: ISO8601 UTC.
- DataFrame: NaN para ausentes; JSON: null (nunca NaN/Infinity).
- synthetic=True solo pruebas/demo de desarrollo; procedencia es la fuente de esta bandera.
- result_id=hash de consulta canónica + checksum de datos + máscara + configuración estadística + versión de código.

### 4.2 Catálogo y guía
```python
@dataclass(frozen=True)
class VariableInfo:
    id: str
    label: str
    definition: str
    unit_monthly: str
    unit_annual: str
    source_id: str
    limitations: tuple[str, ...]

@dataclass(frozen=True)
class RegionSpec:
    id: str
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    mask_version: str
    scale_warning: str

@dataclass(frozen=True)
class QueryParams:
    variable: str
    regions: tuple[str, str]
    start_year: int
    end_year: int
    preset_id: str  # "CR_HEAT" | "CR_RAIN"

def recommend_variable(topic: str) -> dict:
    # topic: "heat" | "rain"; salida: variable, reason, definition
    ...
```

Ejemplo:
```json
{"schema_version":"2.0","topic":"rain","recommendation":{"variable":"PRECTOTCORR","reason":"Permite estudiar cambios en la lluvia acumulada anual; no mide caudal."},"query":{"variable":"PRECTOTCORR","regions":["CR_PN","CR_CAR"],"start_year":1981,"end_year":2024,"preset_id":"CR_RAIN"}}
```
Archivo config/discovery.json: topic, variable, reason, definition. Reglas escritas por Joshua, integración Kevin; NO ranking por p.

### 4.3 Ingesta → preparación
Conservar grid_monthly.parquet: region_id:str, variable:str, lat:float64, lon:float64, time:datetime64[ns], value:float64, unit:str, synthetic:bool.
Clave: (region_id,variable,lat,lon,time). Tabla auxiliar masks.parquet: region_id, lat, lon, weight, mask_version; weight normalizado por sector para máscara activa.
provenance_base.json: provider, source_page, request_urls[], retrieved_at, provider_version:null|string, api_version:null|string, native_resolution_deg:[lat,lon], raw_files[{path,sha256}], transformations[], mask_version, synthetic.
Provider_version desconocida se mantiene null; no usar versión API como versión de datos.

Ejemplo de fila mock:
```json
{"region_id":"CR_PN","variable":"T2M","lat":10.5,"lon":-85.0,"time":"1981-01-01","value":26.4,"unit":"degC","synthetic":true}
```
Las coordenadas son ilustrativas hasta verificar malla; nunca son un resultado real.

### 4.4 Preparación → estadística
RegionalMonthly: region_id, variable, time, value, n_cells_valid:int, n_cells_mask:int, coverage_fraction:float.
RegionalAnnual: region_id, variable, year:int, value:float, unit:str, months_valid:int, complete:bool.
Unidad anual: degC o mm/yr; huecos no se eliminan del eje temporal.
```python
def aggregate_region(grid, masks) -> "RegionalMonthly": ...
def annualize(monthly) -> "RegionalAnnual": ...
def fit_trend(annual, region_id, variable) -> "TrendResult": ...
def adjust_regional_family(results: list) -> list: ...
def adjust_map_family(cell_results) -> tuple: ...
```
Ejemplo mock anual:
```json
{"region_id":"CR_PN","variable":"PRECTOTCORR","year":1981,"value":1800.0,"unit":"mm/yr","months_valid":12,"complete":true}
```

### 4.5 Resultados → servicio/UI
```python
@dataclass(frozen=True)
class TrendResult:
    region_id: str
    variable: str
    start_year: int
    end_year: int
    first_used_year: int | None
    last_used_year: int | None
    n_years: int
    level: str  # none | descriptive | inferential
    status: str # ok | insufficient_data | fit_failed
    slope_per_decade: float | None
    slope_unit: str  # degC/decade | mm/yr/decade
    total_change: float | None
    ci_low: float | None
    ci_high: float | None
    se_hac: float | None
    p_value: float | None
    p_adjusted: float | None
    significant: bool | None
    family_id: str | None
    hac_lags: int | None
    method: str
    coverage_fraction: float
    warnings: tuple[str, ...]
```
Todos los campos son obligatorios; los opcionales usan null. Ejemplo válido de mock:
```json
{"region_id":"CR_PN","variable":"T2M","start_year":2010,"end_year":2024,"first_used_year":2010,"last_used_year":2024,"n_years":15,"level":"descriptive","status":"ok","slope_per_decade":0.2,"slope_unit":"degC/decade","total_change":0.28,"ci_low":null,"ci_high":null,"se_hac":null,"p_value":null,"p_adjusted":null,"significant":null,"family_id":null,"hac_lags":null,"method":"OLS descriptivo","coverage_fraction":1.0,"warnings":["synthetic","short_record"]}
```
CellTrends conserva region_id, variable, lat, lon, slope_per_decade, p_value, q_value, significant(nullable bool), n_years, status. Añade start_year, end_year, slope_unit, level.
Metadatos de familia: family_id, planned_tests, valid_tests, alpha=0.05, method="fdr_by", scope, regions, variables, start_year,end_year. Mapa: scope="cells"; regional: scope="regions". Ejemplo familia regional: "regions|T2M+PRECTOTCORR|CR_PN+CR_CAR|1981-2024|v2".

### 4.6 Servicio real y mock: mismas firmas
```python
def list_variables() -> list[VariableInfo]: ...
def list_regions() -> list[RegionSpec]: ...
def get_coverage() -> dict: ...
def get_annual_series(variable, region_id, start_year, end_year): ...
def get_trend(variable, region_id, start_year, end_year) -> TrendResult: ...
def get_comparison(variable, start_year, end_year, regions=("CR_PN","CR_CAR")) -> dict: ...
def get_cell_trends(variable, region_id, start_year, end_year) -> tuple: ...
def get_event_view(variable) -> list: ... # P1, no bloquear P0
def build_provenance(query: QueryParams) -> dict: ...
def build_evidence_card(query: QueryParams, hypothesis: str = "") -> dict: ...
```
get_trend/get_comparison obtienen ajustes de la familia regional completa, no del subconjunto visible. get_cell_trends calcula/carga familia de ambos sectores antes de devolver uno.
Error de consulta: ValueError legible. Fallos científicos: TrendResult con estado, no excepción para ocultar.
UI nunca calcula pendiente/p; exportación consume el mismo resultado que pantalla.

### 4.7 Ficha de detective y exportación
```json
{"schema_version":"2.0","result_id":"mock-result","preset_id":"CR_HEAT","hypothesis":"Creo que la temperatura ha aumentado.","query":{"variable":"T2M","regions":["CR_PN","CR_CAR"],"start_year":2010,"end_year":2024,"preset_id":"CR_HEAT"},"synthetic":true,"summary":"Hay una pendiente descriptiva; no se evalúa significancia por duración insuficiente.","results":[],"family_metadata":[],"warnings":["short_record","coarse_resolution"],"source_ids":["S1","S2"],"data_sha256":"mock","mask_version":"mock","analysis_version":"2.0","generated_at":"2026-11-14T15:00:00Z"}
```
En real, results contiene ambos TrendResult y family_metadata las familias utilizadas; nunca lista vacía para una consulta exitosa. summary se construye con plantillas deterministas que no inventan valores. Hipótesis no modifica análisis, máscara, período ni datos.
ExportBundle: series_csv:bytes, trends_csv:bytes, provenance_json:bytes, evidence_md:bytes, evidence_json:bytes.
CSV UTF-8, coma, decimal punto; valores numéricos sin redondeo de pantalla. JSON válido; tabla/formato UI puede redondear pero no mostrar p=0 si solo es pequeño.
Provenance añade query, git_commit, data hashes, mask, aggregation, HAC, correction families, limitations y synthetic.
EventAnomaly P1 añade time, value, climatology, anomaly, unit, baseline y etiqueta descriptiva a las filas mensuales; elimina la ambigüedad de una única anomalía sin fecha.

### 4.8 Migración y mocks
Conservar contratos viejos en un adaptador temporal si hay código existente; prueba v1→v2, actualizar UI/fixtures/export en mismo PR. No borrar datos existentes.
M1 grid sintética: Samuel con especificación Emanuel; M2 resultados y casos límite: Emanuel; M3 service_mock: Jacky; M4 ficha y procedencia mock: Samuel/Joshua contenido, Kevin serializa.
Mocks: aumento/disminución conocidos, estacionalidad sin pendiente, AR(1), constantes, faltantes, huecos anuales, n=9/15/30/44, p nulo, BY sin descubrimientos y falla de cobertura.
Bandera synthetic en datos, servicio y export. Tests pueden contener mocks en repo; bloquear su uso como datos de demo/release. Buscar la palabra synthetic no demuestra por sí solo contaminación.

## 5. Roles, entregables y backlog individual
Estimaciones efectivas revisables tras inventario. Meta <=17 h/persona; no llenar todo el margen.

| Persona | Responsabilidad y archivos | Tareas estimadas | Suplente/revisión |
|---|---|---|---|
| Jacky | contracts.py, service.py, service_mock.py, config compartida | auditoría/contratos 2h; servicio+caché 3h; ficha/orquestación 1h; integración 4h; PR/ayuda release 3h; contingencia 2h =15h | Emanuel; no autoaprobar PR |
| Emanuel | prepare.py, statistics.py, tests numéricos | mocks 1h; agregación 2h; HAC/BY/niveles 3h; sensibilidad 1h; validación 3h; integración/textos 2h; contingencia 2h =14h | Jacky revisa con Samuel |
| Samuel | ingest.py, regions.py, build_data.py, data/, DATA_SOURCES.md | fuente/muestra 1h; máscaras CR 2h; ingesta 3h; procedencia 1h; QC 2h; integración/ayuda 2h; contingencia 2h =13h | Emanuel |
| Kevin | app.py, views.py, export.py, .streamlit/config.toml | esqueleto 1h; guía/glosario 1h; series/tarjetas 2h; mapa 2h; ficha/export 1h; integración/UX 3h; contingencia 2h =12h | Jacky técnico, Joshua textos |
| Joshua | config/discovery.json contenido, slides/, pitch/video/limitations | guías/definiciones 1h; narrativa local 1h; contrato equipo 0.5h; slides 3h; README/fuentes 1h; ensayos/video 3h; contingencia 2h =11.5h | Diego slides, Kevin capturas |
| Diego | tests integración, package.ps1, offline check, RELEASE.md | reglas/inventario 1h; contratos 1h; QA 3h; portable 3h; offline 2h; entrega 1h; contingencia 2h =13h | Samuel; apoyo Jacky empaquetado |

### Backlog priorizado con dependencias
| ID | Prioridad | Dueño | Tarea y salida | Dependencia | Aceptación |
|---|---|---|---|---|---|
| J01 | P0 | Jacky | Inventario + contracts v2 + adaptador si aplica | plan actual | todos consumen mismos nombres |
| E01 | P0 | Emanuel | Fixtures numéricas y estados | J01 o ejemplos normativos | cubren niveles/huecos/constantes |
| S01 | P0 | Samuel | Muestra fuente y unidades | ninguna | raw guardado y leído |
| S02 | P0 | Samuel | Máscaras CR y data bundle | S01 | cobertura/resolución/celdas documentadas |
| J02 | P0 | Jacky | service_mock y caché real | J01,E01 | mismas firmas |
| K01 | P0 | Kevin | Interfaz sobre mock | J02 o fixture | recorrido completo marcado synthetic |
| P01 | P0 | Joshua | Glosario y dos guías locales | ninguna | pregunta→variable explicada |
| E02 | P0 | Emanuel | anualización + HAC + BY | E01; real S02 después | pruebas de unidades y familias pasan |
| J03 | P0 | Jacky | Integrar servicio y evidencia | E02,S02 | resultado reproducible por hash |
| K02 | P0 | Kevin | mapas + tarjetas + ficha/export | K01,J03 | UI=CSV=JSON |
| D01 | P0 | Diego | prototipo portable temprano | esqueleto | inicia en segundo equipo |
| D02 | P0 | Diego | QA ciencia/UX/offline | J03,K02 | cero bloqueantes |
| P02 | P0 | Joshua | slides/video con datos verificados | D02 | afirmaciones trazables |
| D03 | P0 | Diego | release y comprobante | freeze | descarga y ejecución verificadas |
| X01 | P1 | Emanuel/Kevin | dos ventanas fijas | P0 validado domingo10 | sin seleccionar mejor p |
| X02 | P1 | Samuel/Emanuel | ENOS y/o IDN/EEP | caché lista y P0 | descriptivo y documentado |
| X03 | P2 | equipo | GLDAS/MODIS/IMERG, MK, PDF | fuera del hackathon salvo margen real | no comprometer P0 |

## 6. Fases paralelas y cronograma
Cinco fases; no esperar datos reales para construir estadísticas/UI. Si el sábado ya avanzó: 20 min de inventario, preservar trabajo y adoptar solo cambios P0 factibles; no reiniciar reloj ni fingir hitos cumplidos.

| Fase | Horario objetivo | Trabajo simultáneo | Integración/aceptación |
|---|---|---|---|
| F1 Base | sáb07–08 | Jacky contratos; Emanuel fixtures; Samuel muestra; Kevin pantalla; Joshua guías; Diego reglas/arranque | I0 a08: mock consumible |
| F2 Componentes | sáb08–13 | datos, ciencia, UI, servicio, QA portable, narrativa | I1 a11: app mock offline; I2 a13: caché CR válida |
| F3 Integración | sáb13–21 | Samuel/Emanuel datos→ciencia; Jacky/Kevin servicio→UI; Diego QA; Joshua relato | I3 a15: un caso real; I4 a19: dos variables + ficha; I5 a21: paquete recuperable |
| F4 Validación | dom07–13 | ciencia, experiencia, portable y relato | I6 a10: P0 verde o cancelar extras; I7 a12: ensayo;13freeze |
| F5 Entrega | dom13–18 | paquete, video, slides, revisión/enlaces | entregar16; margen hasta18 |

### Sábado, hora a hora
| Bloque | Objetivo/checkpoint |
|---|---|
| 07–08 | kickoff20min + inventario + contratos; primera versión mock |
| 08–09 | fuente pequeña, funciones puras, UI esqueleto, prototipo portable |
| 09–10 | validar celdas CR y unidades; primer PR por frente |
| 10–11 | sync10min + pausa10min; guía de preguntas y mocks |
| 11–12 | I1 app mock en segundo equipo; ciencia independiente |
| 12–13 | almuerzo40min; cerrar caché y respaldo I2 |
| 13–14 | primera serie real, agregación y comparación |
| 14–15 | mapas y FDR; I3 real; Joshua adapta capturas |
| 15–16 | sync10min + pausa10min; ficha/export y verificación |
| 16–17 | integrar ambas variables; validar escala/ausentes |
| 17–18 | revisión de UX y evidencia; primer pitch de mesa |
| 18–19 | cena40min + sync10min; I4 lista de bloqueos |
| 19–20 | recorrido real sin red; corregir P0 |
| 20–21 | I5 versión recuperable, hashes, dos copias, plan domingo |
| 21–22 | cierre personal y traslado; sin tareas nuevas |
| 22–06 | ocho horas de sueño protegido |

### Domingo, hora a hora
| Bloque | Objetivo/checkpoint |
|---|---|
| 06–07 | desayuno/traslado |
| 07–08 | sync10min; asignar tres bloqueos máximos |
| 08–09 | validación científica y correspondencia UI/export |
| 09–10 | segundo equipo sin red; medir inicio y consulta |
| 10–11 | I6 sync10min + pausa; solo extras si P0 validado |
| 11–12 | ensayo completo + correcciones de comunicación |
| 12–13 | almuerzo40min; RC; checklist; freeze13 |
| 13–14 | paquete final y grabación sobre misma versión |
| 14–15 | descargar/abrir paquete limpio; segundo ensayo |
| 15–16 | sync10min + pausa; subir y confirmar recepción |
| 16–17 | permisos, enlaces, contingencia |
| 17–18 | presentación y confirmación final |

Metas de rendimiento, no mediciones realizadas: inicio <60s, consulta cacheada <3s. Si un mapa tarda, precalcular consultas permitidas con el mismo método; no degradar p de celdas a otro modelo sin revisión y etiqueta.

## 7. Contrato de trabajo del equipo
**Acuerdo Hefesto v2 — evento:** __________ **lugar:** __________ **fechas:** __________.
Los seis integrantes aceptan el objetivo, alcance, roles, suplencias y entregables de este documento.

1. Disponibilidad: sábado07–21 y domingo07–18, con comidas/pausas y sueño22–06. Puntualidad y aviso de ausencias.
2. Roles: aceptar tabla `5; cada persona mantiene tareas, archivos, rama y siguiente paso actualizados.
3. Decisiones: dueño decide implementación dentro del contrato; Jacky arquitectura; Emanuel con Samuel ciencia; Joshua narrativa; Diego verifica aceptación. Alcance por mayoría tras10min; empate conserva P0. Desempate técnico Jacky o Emanuel si ausente. No votar para convertir evidencia incorrecta en correcta.
4. Comunicación: #hefesto-hackathon; respuesta a mención <=15min durante trabajo; bloqueo a20min con qué falla/qué probé/qué necesito. Sync10min. Sueño y comidas excluidos.
5. Código: ramas feat/,fix/,docs/,chore/; commits tipo(área):acción; prohibido push directo main. PR revisado por otra persona, nunca autoaprobación. Contratos requieren dueño y consumidores; ciencia revisión independiente Jacky/Samuel además de Emanuel autor.
6. Terminado: aceptación, pruebas relevantes, documentación, PR aprobado, integración y demostración. No basta “en mi máquina”.
7. Conflictos: conversación respetuosa10min; Jacky media o Diego si Jacky involucrado. Conductas graves se comunican a organización.
8. Ausencias >45min en bloque activo: suplente toma P0 y Jacky redistribuye; salud/emergencias sin penalización automática. Recortar P1 antes que sueño.
9. Autoría de seis integrantes. Licencia propuesta MIT para código propio; datos/dependencias mantienen sus términos. Portafolio con reconocimiento; compromisos comerciales y cambios de licencia por unanimidad. Premio monetario seis partes iguales tras gastos comunes previamente aprobados y documentados; premios indivisibles por acuerdo y reglas del evento. La firma expresa aceptación.
10. IA: autor humano verifica código/fuentes/resultados y registra uso; no enviar secretos. Las plantillas educativas son deterministas; no necesitan LLM en producción.
11. Bienestar: descanso previsto, sin noche en vela, máximo16h de vigilia planificada y ambiente respetuoso.
12. Freeze13 domingo: corrección crítica de arranque, resultado científico o requisito solo con Jacky+Diego y Emanuel si afecta ciencia; nueva versión y revalidación. No ocultar una función P0 y declarar MVP completo; documentar incumplimiento si no se resuelve.

| Nombre | Rol | Firma | Fecha |
|---|---|---|---|
| Jacky | Arquitectura/integración | __________ | __________ |
| Emanuel | Estadística | __________ | __________ |
| Samuel | Datos | __________ | __________ |
| Kevin | UI/exportación | __________ | __________ |
| Joshua | Producto/pitch | __________ | __________ |
| Diego | QA/release | __________ | __________ |

## 8. Reglas diarias para el canal
1. Máximo dos tareas activas.
2. Un responsable por módulo; cambios ajenos mediante coordinación/PR.
3. Trabaja con mocks mientras llega dato real.
4. Nunca cambies contrato sin avisar consumidores.
5. Bloqueo20min → pedir ayuda con evidencia.
6. Respuesta15min durante trabajo.
7. PR pequeño y revisión ajena; no push directo main.
8. Integrar en cada checkpoint.
9. No inventar fuentes, valores ni resultados.
10. synthetic visible en desarrollo y exportación.
11. No elegir región/período para “conseguir p<0,05”.
12. Toda cifra de pitch tiene result_id/procedencia.
13. Descansos y sueño obligatorios.
14. Freeze13; después solo correcciones críticas aprobadas.
15. Entregar16 y comprobar enlaces desde otra sesión.

## 9. Riesgos y planes B

| Riesgo | Prob. | Impacto | Disparador | Respuesta/dueño |
|---|---|---|---|---|
| API inaccesible | Media | Alto | 30min sin muestra útil | Samuel: caché válida; consultas pequeñas/reintentos; no simular ciencia |
| Malla demasiado gruesa en CR | Alta | Alto | <=1 celda útil o mezcla costa/frontera | Mostrar huella/limitación; etiqueta celda representativa; no inventar detalle/Samuel |
| Datos pesados | Baja | Medio | >200celdas o >20MB procesado | Cajas pequeñas, deduplicar malla, descarga por años/Samuel |
| Unidad mensual confundida | Media | Muy alto | respuesta≠catálogo | parar normalización, verificar conversión/Emanuel+Samuel |
| Huecos de años | Media | Alto | faltante interno | descriptivo con eje real; sin HAC comprimido/Emanuel |
| Inferencia falla | Media | Alto | varianza cero/error | null+estado; usar consulta real validada, no inventar p/Emanuel |
| FDR o familia cambia al ocultar región | Media | Alto | q distinto mismo período | calcular familia completa antes de filtrar/Jacky |
| Signos CR no opuestos | Media | Bajo científicamente | demo lluvia sin contraste | conservar resultados; explicar variabilidad; ENOS como contexto documentado/Joshua |
| Falta tiempo para extras | Alta | Bajo | P0 no verde dom10 | cancelar ENOS/ventanas/MK; conservar guía/ficha básica/Jacky |
| Integración tardía | Media | Alto | I3 no real | sesión conjunta breve, contratos estables/Jacky |
| Portable falla | Media | Muy alto | segundo equipo no arranca sáb11 | Diego+Jacky depuran entorno; confirmar formato jurado temprano |
| Mapas dependen de red | Media | Alto | vacío offline | heatmap y huellas locales, sin teselas/Kevin |

| Pantalla/export/pitch divergen | Media | Alto | cantidades distintas | resultado común por hash; regenerar assets/Diego |
| Error científico después freeze | Baja | Muy alto | validación contradice slide | hotfix revisado y nueva release; informar limitación |
| Ausencia/fatiga | Media | Alto | >45min o malestar | suplente, recorte P1, sueño protegido |
| Fallo carga/permisos | Media | Alto | receptor no abre | entrega16 y segunda sesión/Diego |

## 10. Pitch y demos
Dos demos obligatorias son suficientes: (A) calor y (B) lluvia en Costa Rica. No se requieren dos productos NASA ni dos fenómenos distintos. El mapa representa datos regionales de reanálisis, no capacidad predictiva local.

| Tiempo | Responsable | Acción |
|---|---|---|
| 0:00–0:30 | Joshua | “¿Cómo puede un estudiante de Guanacaste investigar si cambia la lluvia y comparar su evidencia con el Caribe?” |
| 0:30–1:00 | Kevin | Tres preguntas; recomendación explicada; confirmar variable y ventana |
| 1:00–1:50 | Kevin | Caso A calor: series/pendientes/mapas; cifras solo del resultado verificado |
| 1:50–2:40 | Kevin | Caso B lluvia: unidad mm/año; comparar regiones, también si no hay significancia |
| 2:40–3:20 | Emanuel/Samuel | anualización, dependencia temporal, FDR, resolución y procedencia; p no prueba causalidad |
| 3:20–4:00 | Joshua | ficha reproducible y límites; público estudiantil costarricense |
| 4:00–4:30 | Joshua | demo offline y próximos pasos, claramente separados del MVP |

Caso de mecanismo común: ENOS puede modular de modo diferente las lluvias del Pacífico y Caribe costarricenses según investigadores de UCR (S5), pero sus efectos dependen de época/región/otros factores. Esto motiva la hipótesis, no certifica pendientes opuestas en 1981–2024.
Si se implementa P1 ENOS 1997–98: anomalías frente al mismo mes base, etiqueta descriptiva, verificar signos; nunca usar anomalías como evidencia automática de tendencia.
Fuentes y cifras verificadas: docs/claims.csv con claim_id, texto, result_id/source_id, revisor, estado.
Video90–120s desde release final. Si falla demo: reproducir video real; no simular resultados.
Preguntas: Jacky arquitectura/IA; Emanuel métodos; Samuel datos/escala; Kevin UX; Joshua valor educativo; Diego reproducibilidad.

## 11. Checklist de entrega
### Ciencia
- [ ] T2M y PRECTOTCORR reales, unidades y cobertura verificadas.
- [ ] Máscaras CR y huellas nativas documentadas; no precisión municipal/finca.
- [ ] Anualización correcta y años incompletos visibles.
- [ ] Inferencia válida en consulta histórica; niveles y huecos probados.
- [ ] HAC y sensibilidad documentados; IC individual.
- [ ] Familias regional y mapas explícitas; q no depende de ocultar regiones.
- [ ] No se fuerza significancia ni contraste.
- [ ] Conceptos ciclo, anomalía, tendencia y causalidad diferenciados.
### Producto
- [ ] Tres preguntas recomiendan y explican variable.
- [ ] Dos guías locales calor/lluvia.
- [ ] Qué/dónde/cuánto/significancia visibles.
- [ ] Ficha con result_id, fuentes, máscara, método y límites.
- [ ] UI=export=slides; ningún dato sintético en release de demostración.
### Ingeniería
- [ ] Contratos v2 y mocks compatibles; PR aprobado.
- [ ] Datos cacheados, hashes y versiones registradas.
- [ ] Pruebas relevantes pasan; cero bloqueantes.
- [ ] Formato ejecutable aceptado [verificar].
- [ ] Segundo equipo sin red y dependencias de desarrollo.
- [ ] Mapa sin teselas externas, telemetría desactivada.
- [ ] Repo/LICENSE/THIRD_PARTY/AI_USAGE/README/RELEASE completos.
- [ ] Entrega y permisos confirmados a16; respaldo USB/video.
### Equipo
- [ ] Acuerdo aceptado por seis personas.
- [ ] Suplencias y Q&A ensayados.
- [ ] Descansos/sueño respetados.

## Fuentes verificadas y pendientes
Consulta: 14 noviembre2026. Los enlaces sustentan acceso/métodos/contexto; no son evidencia de un resultado calculado por Hefesto.
- S1 NASA POWER Monthly API: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- S2 NASA POWER Meteorological Data Sources: https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
- S3 statsmodels robust covariance/HAC: https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html
- S4 statsmodels multipletests: https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html
- S5 UCR, investigadores explican ENOS y efectos regionales (12 julio2023): https://www.ucr.ac.cr/noticias/2023/7/12/el-nino-y-la-nina-dos-caras-de-un-mismo-fenomeno-climatico/
- S6 Streamlit ejecución local: https://docs.streamlit.io/develop/concepts/architecture/run-your-app
- [verificar] pestaña Resources y enlace original del video del reto; no recibidos.
- [verificar] costa/fronteras para máscara y licencia del recurso finalmente usado.
- [verificar] endpoints concretos, cobertura, unidades y límites mediante muestra real.
- La transcripción usa “AODD”; la sigla habitual de profundidad óptica de aerosoles es AOD. No agregar esa variable al MVP por aparecer en el ejemplo del video.
