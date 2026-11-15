"""API independiente o router integrable al FastAPI existente."""
from typing import Literal
import logging
from fastapi import APIRouter, FastAPI, HTTPException, Query
from .engine import ForecastEngine, NeedsRevalidation

router = APIRouter(prefix='/api/predicciones', tags=['Predicciones experimentales'])

@router.get('')
def predictions(region: Literal['CR','CR_PN','CR_CAR']='CR',
                variable: Literal['T2M','RH2M','PRECTOTCORR','UV']='T2M',
                start: str | None = None, months: int = Query(6, ge=1, le=6)):
    try:
        # Carga pequeña. No se ejecuta el backtest ni se descarga nada por solicitud.
        return ForecastEngine().forecast(region, variable, start, months)
    except NeedsRevalidation as exc:
        raise HTTPException(503, str(exc)) from exc
    except (OSError, KeyError) as exc:
        logging.exception('Datos de pronóstico no disponibles')
        raise HTTPException(503, 'No se pudieron cargar los datos del modelo.') from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

app = FastAPI(title='Hefesto: predicciones experimentales')
app.include_router(router)
