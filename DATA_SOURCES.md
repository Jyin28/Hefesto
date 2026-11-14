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
