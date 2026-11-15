# Terceros

## Datos
- **NASA POWER** (Prediction Of Worldwide Energy Resources), API mensual regional, variables T2M y PRECTOTCORR, 1981–2024.
  Datos abiertos de la NASA; se pide reconocer la fuente. https://power.larc.nasa.gov/ — Reanálisis MERRA-2 (GMAO/NASA).
  Hefesto los trata como estimaciones de modelo, no como medición directa.
- Los archivos `data/raw/*.json` son la respuesta original sin modificar (huellas SHA-256 en `data/processed/provenance_base.json`).

## Dependencias principales (ver `requirements.txt`, versiones congeladas)
| Paquete | Uso | Licencia |
|---|---|---|
| streamlit | interfaz web local | Apache-2.0 |
| plotly | gráficos y mapa de celdas (sin teselas externas) | MIT |
| pandas / numpy / pyarrow | datos y Parquet | BSD-3 / BSD-3 / Apache-2.0 |
| statsmodels / scipy | solo para pruebas de contraste de la estadística propia | BSD-3 |
| pytest | pruebas | MIT |

`src/web_api.py`, `web/` y `requirements-web.txt` (FastAPI/React) no forman parte del producto MVP.

## Fuentes de contexto
UCR (ENOS en Costa Rica, 2023); statsmodels (HAC, multipletests); Streamlit docs.
