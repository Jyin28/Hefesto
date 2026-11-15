"""FastAPI routes used by the React app."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .contracts import COVERAGE_END_YEAR, COVERAGE_START_YEAR
from .web_data import ROOT, local_catalog
from .export import csv_tables, evidence_card, format_csv

app = FastAPI(title="Detective Tico", version="0.1.0")
logger = logging.getLogger(__name__)


@app.get("/api/local")
def get_local():
    return local_catalog()


@app.get("/api/clima/{region}/{variable}")
@app.get("/api/ficha/{region}/{variable}")
def get_climate(region: str, variable: str, desde: int = COVERAGE_START_YEAR, hasta: int = COVERAGE_END_YEAR,
                a_inicio: int | None = None, a_fin: int | None = None,
                b_inicio: int | None = None, b_fin: int | None = None,
                celda: str | None = None, canton: str | None = None, tabla: str | None = None):
    try:
        periods = a_inicio, a_fin, b_inicio, b_fin
        if any(year is not None for year in periods) and any(year is None for year in periods):
            raise ValueError("Indique los cuatro años de inicio y fin de A y B")
        card = evidence_card(
            region, variable, start=desde, end=hasta, cell_id=celda, canton=canton,
            window_a=(a_inicio, a_fin) if a_inicio is not None else None,
            window_b=(b_inicio, b_fin) if b_inicio is not None else None,
        )
        if tabla is not None:
            tables = csv_tables(card)
            if tabla not in tables:
                raise ValueError("Tabla CSV desconocida")
            if not tables[tabla]:
                raise HTTPException(status_code=404, detail="La ficha no contiene datos para esta tabla")
            return Response(format_csv(tables[tabla]), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="{tabla}.csv"'})
        return card
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except OSError as error:
        logger.exception("No se pudieron leer los datos climáticos")
        raise HTTPException(status_code=503, detail="Datos climáticos temporalmente no disponibles") from error


dist = ROOT / "web" / "dist"
if (dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
