# Fuentes de Datos y Limitaciones Espaciales — Hefesto v2

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
