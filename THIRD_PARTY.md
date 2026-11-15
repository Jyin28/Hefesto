# Terceros

## Datos
- **NASA POWER** (Prediction Of Worldwide Energy Resources), API mensual regional, variables T2M y PRECTOTCORR, 1981–2024.
  Datos abiertos de la NASA; se pide reconocer la fuente. https://power.larc.nasa.gov/ — Reanálisis MERRA-2 (GMAO/NASA).
  Hefesto los trata como estimaciones de modelo, no como medición directa.
- Los archivos `data/raw/*.json` son la respuesta original sin modificar (huellas SHA-256 en `data/processed/provenance_base.json`).
- **NASA POWER, variables adicionales** `RH2M` (humedad, 1981–2024) y `ALLSKY_SFC_UV_INDEX` (UV, 2001–2024, malla de 1°) para las capas del mapa. Sus JSON crudos también están en `data/raw/`; su huella SHA-256 va en `snapshot.layers[*].provenance`.
- **OpenStreetMap / HOT** — hidrografía de Costa Rica (`data/raw/hidrografia/`), © colaboradores de OpenStreetMap, licencia **ODbL 1.0** (https://opendatacommons.org/licenses/odbl/1-0/). Obliga a atribuir la fuente (se muestra en el mapa de cuencas) y a compartir igual las bases de datos derivadas.
- **SAGA (AyA)** — «Operadores y Fuentes (Ubicaciones)»: entes operadores de agua y sus fuentes, con su último caudal registrado. Datos al 11 de noviembre de 2026.

## Dependencias principales (ver `requirements.txt`, versiones congeladas)
| Paquete | Uso | Licencia |
|---|---|---|
| streamlit | interfaz web local | Apache-2.0 |
| plotly | gráficos y mapa de celdas (sin teselas externas) | MIT |
| pandas / numpy / pyarrow | datos y Parquet | BSD-3 / BSD-3 / Apache-2.0 |
| statsmodels / scipy | solo para pruebas de contraste de la estadística propia | BSD-3 |
| pytest | pruebas | MIT |

`src/web_api.py` y `web/` (FastAPI/React) no forman parte del producto MVP.

## Fuentes de contexto
UCR (ENOS en Costa Rica, 2023); statsmodels (HAC, multipletests); Streamlit docs.
