# Terceros

## Datos
- **NASA POWER** (Prediction Of Worldwide Energy Resources), API mensual regional, variables T2M y PRECTOTCORR, 1981–2024.
  Datos abiertos de la NASA; se pide reconocer la fuente. https://power.larc.nasa.gov/ — Reanálisis MERRA-2 (GMAO/NASA).
  AguaAlerta los trata como estimaciones de modelo, no como medición directa.
- Los archivos `data/raw/*.json` son la respuesta original sin modificar (huellas SHA-256 en `data/processed/provenance_base.json`).
- **NASA POWER, variables adicionales** `RH2M` (humedad, 1981–2024) y `ALLSKY_SFC_UV_INDEX` (UV, 2001–2024, malla de 1°) para las capas del mapa. Sus JSON crudos también están en `data/raw/`; su huella SHA-256 va en `snapshot.layers[*].provenance`.
- **Copernicus Climate Change Service (C3S) / ECMWF** — ERA5-Land (`reanalysis-era5-land-monthly-means`) y ERA5 niveles únicos (`reanalysis-era5-single-levels-monthly-means`), descargados con la API del Climate Data Store (https://cds.climate.copernicus.eu) para el mapa «Datos CDS». Licencia Copernicus: se debe atribuir («Contiene información modificada del Servicio de Cambio Climático de Copernicus») y ni la Comisión Europea ni ECMWF responden por el uso que se haga de ella. Los NetCDF originales van en `data/raw/cds/`.
- **OpenStreetMap / HOT** — hidrografía de Costa Rica (`data/raw/hidrografia/`), © colaboradores de OpenStreetMap, licencia **ODbL 1.0** (https://opendatacommons.org/licenses/odbl/1-0/). Obliga a atribuir la fuente (se muestra en el mapa de cuencas) y a compartir igual las bases de datos derivadas.
- **SAGA (AyA)** — «Operadores y Fuentes (Ubicaciones)»: entes operadores de agua y sus fuentes, con su último caudal registrado. Datos al 11 de noviembre de 2026.
- **Fotografías de la página de inicio** (`web/public/img/`), de Wikimedia Commons. Las de licencia CC BY-SA obligan a atribuir y a compartir igual las versiones modificadas (se redimensionaron y comprimieron):
  - `hero.jpg` — Cephas, CC BY-SA 4.0: https://commons.wikimedia.org/wiki/File:Monteverde_Reserve_Costa_Rica_02.jpg
  - `nino.jpg` — MongeNajera, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:Rio_Guanacaste.jpg
  - `cds.jpg` — Dr. Alexey Yakovlev, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Monteverde_Cloud_Forest_(28367816878).jpg
  - `nasa.jpg` — NASA Goddard Space Flight Center, dominio público: https://commons.wikimedia.org/wiki/File:Costa_Rica_(14214278247).jpg
  - `nacionales.jpg` — Bernard Gagnon, CC0: https://commons.wikimedia.org/wiki/File:Sierpe_River,_Costa_Rica.jpg
  - `costa.jpg` — PoeXinia, CC0: https://commons.wikimedia.org/wiki/File:Beach_on_the_Pacific_Coast_of_Costa_Rica.jpg

## Dependencias principales (ver `requirements.txt`, versiones congeladas)
| Paquete | Uso | Licencia |
|---|---|---|
| streamlit | interfaz web local | Apache-2.0 |
| plotly | gráficos y mapa de celdas (sin teselas externas) | MIT |
| pandas / numpy / pyarrow | datos y Parquet | BSD-3 / BSD-3 / Apache-2.0 |
| statsmodels / scipy | solo para pruebas de contraste de la estadística propia | BSD-3 |
| cdsapi / xarray / netCDF4 | descarga y lectura de los datos del CDS (`src/cds.py`, mapa «Datos CDS») | Apache-2.0 / Apache-2.0 / MIT |
| pytest | pruebas | MIT |

`src/web_api.py` y `web/` (FastAPI/React) no forman parte del producto MVP.

## Fuentes de contexto
UCR (ENOS en Costa Rica, 2023); statsmodels (HAC, multipletests); Streamlit docs.
