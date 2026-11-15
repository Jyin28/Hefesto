# Fuentes de Datos y Limitaciones Espaciales — AguaAlerta v2

## 1. Fuente primaria (S1 / S2)
* **Proveedor:** NASA POWER (MERRA-2 assimilation)
* **Endpoint:** NASA POWER Monthly and Annual Regional API (`v2.10.0`)
* **Documentacion oficial:** https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
* **Variables:**
  * `T2M`: Temperatura del aire a 2 metros (`degC` mensual; media anual ponderada por dias en `degC`).
  * `PRECTOTCORR`: Precipitacion corregida (`mm/day` mensual; acumulado anual en `mm/yr`).
* **Cobertura temporal:** 1981-01 a 2024-12 (528 meses por celda).
* **Fecha de extraccion (UTC):** `2026-11-14T17:13:44Z`
* **Licencia:** Datos abiertos de acceso publico NASA POWER (sin autenticacion Earthdata requerida).

## 2. Mascara geografica y sectores de Costa Rica (`cr-land-mask-v2.0`)
* **Fuente de mascara:** Verificacion de centros de celda nativa NASA POWER (0.5x0.625 deg) contra limites terrestres oficiales de Costa Rica (WGS84), excluyendo celdas con centro oceanico.
* **Resolucion nativa:** `0.5 deg latitud x 0.625 deg longitud` (~55 km x 69 km en Costa Rica).
* **Sectores:**
  * `CR_PN` — Sector Pacifico Norte (entorno regional de Guanacaste): bbox `[-86.0, 9.75, -85.0, 11.25]` (5 celdas terrestres).
  * `CR_CAR` — Sector Caribe (entorno regional de Limon): bbox `[-84.0, 9.5, -82.75, 10.75]` (5 celdas terrestres).
* **Ponderacion espacial:** Promedio ponderado por `cos(lat)` normalizado por sector.

## 3. Limitaciones cientificas obligatorias
1. **Reanalisis, no estaciones locales:** NASA POWER entrega estimaciones de modelo atmosferico con asimilacion de observaciones (MERRA-2), no mediciones directas de pluviometros o termometros locales.
2. **Escala regional:** Cada celda cubre decenas de kilometros; no representa fincas, cantones ni cuencas especificas.
3. **Mezcla costera y orografia:** Las celdas costeras incluyen fraccion oceanica y suavizan gradientes abruptos de las cordilleras de Costa Rica.
4. **Uso educativo:** Herramienta de exploracion historica; no pronostica sequias, inundaciones ni disponibilidad de agua potable.

## 3b. Región nacional `CR` (interfaz web)
* La descarga ya cubre la malla 7x7 completa (49 celdas). Para el mapa nacional se usan las celdas con al menos 1 % de tierra según `data/web/national_cells.json` (24 celdas), generado por `web/scripts/build-geo.mjs` desde la capa cantonal.
* Promedio nacional ponderado por `cos(lat) × fracción de tierra`; tiene su propia familia de pruebas BY (celdas nacionales) y no altera las pruebas de los dos sectores.
* Cada cantón usa la celda de la malla que más lo cubre (`cantonCells` en `web/public/data/geo.json`). Los contornos de Nicaragua y Panamá del mapa son aproximados, dibujados a mano.

## 4. Qué datos usa el producto MVP (y cuáles no)
**Usados:** `data/raw/nasa_power_monthly_{T2M,PRECTOTCORR}_1981_2024.json` (crudo inmutable, SHA-256 en
`provenance_base.json`), `data/processed/grid_monthly.parquet` (10 560 registros, 5 celdas × 2 sectores × 528 meses × 2 variables),
`data/processed/masks.parquet`, `data/processed/provenance_base.json`, `data/web/enso.json` (episodios ENOS) y `config/discovery.json`.
Verificados con `scripts/verify_data.py` (esquema, unidades, celdas, 528 meses/celda, sin NaN ni fill values, Parquet == crudo).

**No usados por el producto** (se conservan en el repo como insumos): las tres hojas de cálculo de AyA/anomalía cantonal,
`data/processed/water_*.csv`, `data/web/local.json` y `cantons.json`, `data/mock/` (solo pruebas), la rama `feat/samuel-data-cr`
(`data/processed` allí son datos de relleno: precipitación casi constante y celdas marinas; **no usar**).

## 5. Limitación adicional detectada
Las celdas del Caribe incluyen terreno alto (Talamanca): T2M medio ≈ 22 °C, menor que el de la costa de Limón.
La lluvia de reanálisis no está validada con estaciones (ver `docs/limitations.md` §9).

## 6. Capas adicionales del mapa (humedad, UV, hidrografía y operadores)

- **Humedad relativa a 2 m (`RH2M`)**: NASA POWER Monthly Regional, misma malla 0,5° × 0,625° y años 1981–2024 que T2M y lluvia. Promedio anual ponderado por días; un año sin los 12 meses válidos no se usa.
- **Radiación UV (`ALLSKY_SFC_UV_INDEX`)**: NASA POWER la publica solo desde 2001 y en malla nativa de 1° × 1°. Es un promedio de las 24 horas del día (incluye la noche), por eso es mucho menor que el índice UV del mediodía. Cada celda del mapa toma el punto de NASA más cercano a su centro, así que varias celdas vecinas comparten valor (`resampled: true` en el snapshot).
- **Hidrografía**: HOT/OpenStreetMap (`hotosm_cri_waterways_osm_geojson.zip`, instantánea del 2026-11-03), licencia ODbL: se debe atribuir «© colaboradores de OpenStreetMap». Es cobertura voluntaria y puede estar incompleta. Muestra dónde hay ríos y quebradas; **no mide caudal**.
- **Operadores de agua**: SAGA (AyA), «Operadores y Fuentes (Ubicaciones)», datos al 11 de noviembre de 2026. Caudal inicial de cada operador = suma del «Último caudal registrado» de sus fuentes, que se asume en L/s. 1175 de 1334 operadores tienen al menos una medición. Los reportes que envían las ASADAs son autorreportes sin verificación independiente.

## 7. Mapa «Datos CDS» (Copernicus Climate Data Store)

Tercer mapa de la interfaz web: una cuadrícula de **0,1° × 0,1°** (~11 km, 505 cuadros con al menos 1 % de tierra) con las mismas cuatro capas que el mapa de NASA POWER. Se genera con `python -m src.cds` y se guarda en `web/public/data/cds.json`; la malla sale de `npm run geo` (`web/public/data/geo-cds.json`, `data/web/cds_cells.json`). No toca `snapshot.json` ni `provenance_base.json`.

| Capa | Producto CDS | Variable(s) | Conversión |
|---|---|---|---|
| Temperatura (`T2M`) | ERA5-Land medias mensuales, 0,1° (`reanalysis-era5-land-monthly-means`, DOI 10.24381/cds.68d2bb30) | `2m_temperature` | K − 273,15 → °C |
| Lluvia (`PRECTOTCORR`) | ERA5-Land | `total_precipitation` | m/día × 1000 → mm/día, y × días del mes → mm/año |
| Humedad (`RH2M`) | ERA5-Land | `2m_temperature` y `2m_dewpoint_temperature` | Fórmula de Magnus (Alduchov y Eskridge), tope 100 % |
| Radiación UV (`UV`) | **ERA5** niveles únicos, medias mensuales, 0,25° (`reanalysis-era5-single-levels-monthly-means`, DOI 10.24381/cds.f17050d7) | `downward_uv_radiation_at_the_surface` | J/m² por día ÷ 86 400 → W/m² |

- **Cobertura:** 1981–2024 para las cuatro capas (el UV de CDS no está limitado a 2001 como el de NASA). Promedio anual ponderado por días; un año sin los 12 meses válidos queda sin dato. El promedio nacional pesa `cos(lat) × fracción de tierra` sobre los cuadros con dato.
- **Reanálisis, no satélite puro:** ERA5 y ERA5-Land son reanálisis (modelo que asimila observaciones de satélite y estaciones). Misma advertencia que NASA POWER: no son mediciones locales.
- **UV remuestreado:** ERA5-Land no publica UV, así que cada cuadro de 0,1° toma el punto de ERA5 (0,25°) más cercano a su centro; varios cuadros vecinos comparten valor (`resampled: true`).
- **UV en W/m², no índice UV:** es la energía UV-A + UV-B que llega al suelo promediada las 24 h (incluye la noche). Las escalas de NASA (índice) y de CDS (W/m²) **no son comparables**.
- **Humedad aproximada:** se calcula con las medias mensuales de temperatura y punto de rocío, no como media de humedades horarias; sesga ligeramente la humedad media mensual.
- **Costa y mar:** ERA5-Land no tiene valores sobre el mar; los cuadros costeros sin dato quedan en gris y no entran en el promedio.
- **Comprobación de unidades:** `src/cds.py` se niega a escribir una capa con valores fuera de rangos plausibles (p. ej. lluvia anual fuera de 200–15 000 mm, UV fuera de 0,5–60 W/m²), para que un error de unidades no llegue al mapa.
- **UV opcional:** el archivo de ERA5 (UV) puede faltar. Sin él, `python -m src.cds` publica solo temperatura, lluvia y humedad y el botón UV se desactiva en «Datos CDS»; al agregar el archivo y volver a correr el comando, la capa aparece sola. El UV **nunca se descarga solo**: hace falta el archivo en `data/raw/cds/` o la opción `--download-uv` (necesita clave del CDS).
- **Archivos descargados a mano:** si `data/raw/cds/era5land_monthly_1981_2024.nc` existe sin su `.meta.json`, se registra su SHA-256 (`downloaded_manually: true`) y no se pide nada al CDS. Puede traer más años o una caja más grande que la necesaria; solo se usan 1981–2024 y las celdas del mapa.
- **Caché:** los NetCDF originales quedan en `data/raw/cds/` con su `.meta.json` (SHA-256, solicitud, fecha). Si existen, no se vuelve a descargar.
- **Licencia y atribución:** licencia Copernicus (datos abiertos con atribución). Texto mostrado en el mapa: «Contiene información modificada del Servicio de Cambio Climático de Copernicus (C3S, 2026)».
