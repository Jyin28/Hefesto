# Detective Tico

React consulta datos climáticos de NASA POWER de Pacífico Norte y Caribe. El buscador usa los 84 cantones de la DTA 2026. Santa Cruz y Limón enlazan a los sectores para el piloto. Las series corresponden a celdas climáticas o al promedio regional.

## Ejecutar en desarrollo

Desde la raíz de `Hefesto`, en una terminal PowerShell con Python y Node.js instalados:

```powershell
python -m pip install -r requirements-web.txt
python -m src.web_data
python -m uvicorn src.web_api:app --reload
```

En otra terminal, desde la misma raíz:

```powershell
cd web
npm.cmd install
npm.cmd run dev
```

Abrí `http://localhost:5173`. Vite envía `/api` a FastAPI en el puerto `8000`. `http://127.0.0.1:8000/docs` permite probar las rutas. Para probar una compilación servida por FastAPI, ejecutá `npm run build` dentro de `web/` y reiniciá Uvicorn desde la raíz.

También podés servir `web/dist` como página estática después de generar la copia JSON y compilar. React consulta la API cuando está disponible y usa la copia incluida en la compilación cuando la API no responde. Los cambios en avisos requieren regenerar la copia para el modo estático.

El snapshot incluye el detalle de celdas para las ventanas por defecto. La API permite cambiar las ventanas y descargar CSV/JSON desde React. Streamlit ofrece estas consultas desde el mismo paquete de datos local.

## Cartografía y avisos

- `python scripts/prepare_cantons.py --ign` consulta la capa publicada del IGN y exige que sus códigos coincidan con la DTA 2026. Si la fuente no responde, usá el flujo con un archivo local. Antes de publicar, cotejá la geometría, su fecha y condiciones de uso.
- Prepará un GeoJSON cantonal en EPSG:4326, con código oficial de tres dígitos, nombre y provincia. Si pesa varios MB, simplificalo para visualización con QGIS y conservá los límites compartidos. Guardá el archivo de origen y su ficha con fuente, fecha, cobertura y condiciones de uso.
- Corré `python scripts/prepare_cantons.py ruta/al/archivo.geojson --code-field CAMPO_CODIGO --name-field CAMPO_NOMBRE --province-field CAMPO_PROVINCIA` desde la raíz. Esto coloca la capa en `web/public/data/cantones.geojson`. Verificá el número de cantones y que la selección de Santa Cruz coincida con su ficha. La aplicación usa sectores climáticos como respaldo mientras falta la capa.
- `npm.cmd run geo` (dentro de `web/`) precalcula `public/data/geo.json` a partir de `cantones.geojson`: contorno del país, provincias, contornos aproximados de Nicaragua y Panamá, la malla NASA POWER 7×7 con su porción de tierra y la celda que más cubre a cada cantón. También escribe `data/web/national_cells.json`, que usa Python para la región nacional `CR`. Corrélo después de cambiar la capa cantonal y antes de `python -m src.web_data`. Los contornos de los vecinos son dibujados a mano (aproximados, solo para que el mapa no flote en el vacío).
- Las asociaciones de cantón a sector están en `data/web/cantons.json`. Editá `data/web/local.json` para directorio, comunicados y registros hídricos. Conservá alcance geográfico, fecha, fuente y condición programada u observada.
- Una vez cargado un aviso, la URL `/?canton=503&vista=agua&aviso=<id>` abre la ficha y destaca ese comunicado. `/?canton=503&vista=clima` abre las tendencias.

## Capas del mapa, hidrografía y operadores de agua

Estos pasos generan los archivos que el navegador pide en `web/public/data/` (versionados en git para que la web funcione al clonar; regeneralos con estos pasos si cambian las fuentes).

- `python -m src.web_data` también escribe `snapshot.layers`: promedios anuales por celda de temperatura, lluvia, humedad (`RH2M`, 1981–2024) y radiación UV (`ALLSKY_SFC_UV_INDEX`, solo 2001–2024). La primera vez descarga RH2M y UV de NASA POWER y los guarda en `data/raw/`. El UV llega en malla de 1° y cada celda del mapa toma el punto más cercano.
- `python scripts/prepare_waterways.py` lee `data/raw/hidrografia/hotosm_cri_waterways_osm_geojson.zip` (OpenStreetMap, ODbL) y escribe `public/data/waterways.geojson` (~4,5 MB, simplificado). Solo se pide al abrir el mapa de cuencas.
- `python scripts/prepare_asadas.py` lee `data/raw/agua/Operadores y Fuentes (Ubicaciones).xlsx` y escribe `data/web/asadas.json` y su copia en `public/data/`: 1334 operadores de agua con provincia, cantón, distrito y caudal inicial (suma del último caudal de sus fuentes, en L/s). No se dibujan en el mapa; se buscan con el buscador o con «Buscar por lugar».
- Cada cuenta de `src/data/admins.json` administra una sola ASADA (`asadaId` = IDEO de SAGA) y solo puede enviar reportes sobre ella. Los reportes (caudal, afectación por El Niño y localidades) se guardan en `localStorage`; el caudal vigente es el del reporte más reciente. Las cuentas son de demostración, sin seguridad real.

## API

| Ruta | Resultado |
|---|---|
| `GET /api/local` | Catálogo cantonal, operadores y comunicados cargados. |
| `GET /api/clima/CR_PN/PRECTOTCORR` | Serie anual regional, comparación de períodos, tendencia y fuente. |
| `GET /api/clima/CR_CAR/T2M?desde=1991&hasta=2024` | El mismo contrato con otro período y variable. |
| `GET /api/clima/CR_CAR/T2M?a_inicio=1981&a_fin=2000&b_inicio=2005&b_fin=2024` | Ventanas explícitas. El selector `celda` acepta un ID incluido en la respuesta. |
| `GET /api/ficha/CR_PN/PRECTOTCORR?canton=503&tabla=water` | CSV del indicador de agua de la ficha. Tablas disponibles: `series`, `results`, `water`, `distribution`, `enso` y `sources`. Omití `tabla` para JSON. |

## Entregas para el piloto

| Quién | Entrega |
|---|---|
| Samuel | GeoJSON cantonal vigente con metadatos y revisión de la asociación cantón–zona climática. |
| Joshua | Un comunicado de agua verificable con enlace original, fecha y comunidades. Nombre y contacto de la ASADA u operador que atiende esas comunidades. |
| Jacky | Confirmar el contrato API y dónde quedará accesible para la demo. El archivo `src/web_api.py` ya expone las rutas iniciales. |
| Kevin | Probar el flujo de la maqueta en escritorio y celular y ajustar la jerarquía visual del mapa y la ficha. |
| Diego | Verificar selección por mapa y buscador, enlace de WhatsApp y correspondencia de los gráficos con la API y su copia estática. |
| Emanuel | Revisar la interpretación y las unidades de la comparación y de la tendencia mostradas en la ficha. |
