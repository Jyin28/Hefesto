"""Calcula estimaciones al solicitarse. No lee predicciones precalculadas."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import numpy as np
import pandas as pd
from .models import predict_models, physical

DATA = Path(__file__).parent / 'data'
REGIONS = ('CR', 'CR_PN', 'CR_CAR')
VARIABLES = ('T2M', 'RH2M', 'PRECTOTCORR', 'UV')

class NeedsRevalidation(ValueError):
    pass

def validate_series(series):
    if len(series) < 120 or not series.index.is_unique:
        raise ValueError('Se requieren al menos 120 meses sin duplicados.')
    if not series.index.is_monotonic_increasing:
        raise ValueError('Los meses deben estar ordenados.')
    expected = pd.date_range(series.index[0], series.index[-1], freq='MS')
    if not series.index.equals(expected) or not np.isfinite(series.values).all():
        raise ValueError('Serie con meses ausentes, fechas inválidas o valores no finitos.')

class ForecastEngine:
    def __init__(self, data_dir=DATA):
        root = Path(data_dir)
        self.policy = json.loads((root / 'calibration.json').read_text(encoding='utf-8'))
        for name, expected in self.policy['input_sha256'].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
                raise NeedsRevalidation('Los datos cambiaron: repetir la validación antes de reutilizar modelos y bandas.')
        self.frame = pd.read_csv(root / 'monthly_regional.csv')
        rr = pd.read_csv(root / 'roni_noaa.csv')
        self.roni = pd.Series({pd.Timestamp(int(row['year']), m, 1): row.iloc[m]
                              for _, row in rr.iterrows() for m in range(1, 13)
                              if pd.notna(row.iloc[m])}).sort_index()

    def forecast(self, region='CR', variable='T2M', start=None, months=6):
        if region not in REGIONS or variable not in VARIABLES:
            raise ValueError('Región o variable no admitida. No hay pronósticos por cantón.')
        if not isinstance(months, int) or not 1 <= months <= 6:
            raise ValueError('months debe estar entre 1 y 6.')
        if start is None:
            today = datetime.now(ZoneInfo('America/Costa_Rica'))
            start = (pd.Timestamp(today.year, today.month, 1) + pd.DateOffset(months=1)).strftime('%Y-%m')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', start):
            raise ValueError('start debe tener formato YYYY-MM.')
        if start < self.policy['first_target']:
            raise ValueError('Esta calibración no sirve para simular emisiones anteriores a diciembre de 2026.')
        source = 'POWER' if variable == 'UV' else 'CDS'
        df = self.frame[(self.frame.source == source) & (self.frame.region == region) & (self.frame.variable == variable)]
        s = pd.Series(df.value.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(df.date)))
        validate_series(s)
        key = f'{source}/{region}/{variable}'
        targets = pd.date_range(start + '-01', periods=months, freq='MS')
        last = s.index[-1]
        horizons = [(t.year-last.year)*12+t.month-last.month for t in targets]
        policy = self.policy['series'].get(key)
        # No extrapolar el modelo fuera de los horizontes que se probaron.
        allowed = [h for h in horizons if policy and 1 <= h <= policy['max_contiguous_horizon']]
        predictions = {}
        if allowed:
            result, sigma, _ = predict_models(s, len(s)-1, allowed, self.roni)
            values = physical(result[policy['model']], variable)
            for h, value, sd in zip(allowed, values, sigma):
                if not np.isfinite(value) or not np.isfinite(sd):
                    raise ValueError('No se puede ajustar el modelo: revisar RONI y observaciones.')
                q = policy['horizons'][str(h)]['q90']
                predictions[h] = (float(value), float(physical(value-q*sd, variable)), float(physical(value+q*sd, variable)))
        base = s.loc['2001-01':'2024-12'] if variable == 'UV' else s.loc['1991-01':'2020-12']
        rows = []
        for target, h in zip(targets, horizons):
            v = base[base.index.month == target.month]
            if variable == 'PRECTOTCORR':
                v = v * v.index.days_in_month
            estimate = low = high = None
            status = 'forecast_unavailable' if variable == 'T2M' else 'seasonal_reference'
            reason = 'Sin habilidad predictiva suficiente en este horizonte; se muestra referencia histórica.'
            validation = None
            if h in predictions:
                factor = target.days_in_month if variable == 'PRECTOTCORR' else 1
                estimate, low, high = [x*factor for x in predictions[h]]
                status = 'experimental_forecast'
                reason = 'Estimación regional experimental, no validada con estaciones.'
                validation = policy['horizons'][str(h)]
            if variable == 'UV':
                reason = 'NASA local termina en 2024-12. UV medio de 24 horas, no máximo del mediodía.'
            rows.append({'target_month': target.strftime('%Y-%m'), 'lead_months': h,
                         'status': status, 'estimate': estimate, 'lower90': low, 'upper90': high,
                         'reason': reason, 'validation': validation,
                         'reference': {'mean': float(v.mean()), 'p10': float(v.quantile(.1)),
                                       'p90': float(v.quantile(.9)), 'n_years': len(v),
                                       'period': '2001-2024' if variable == 'UV' else '1991-2020',
                                       'kind': 'historical_distribution_not_prediction_interval'}})
        return {'region': region, 'variable': variable, 'source': source,
                'native_variable': {'T2M':'t2m','RH2M':'t2m+d2m','PRECTOTCORR':'tp','UV':'ALLSKY_SFC_UV_INDEX'}[variable],
                'unit': {'T2M':'°C','RH2M':'%','PRECTOTCORR':'mm/mes','UV':'Índice UV medio 24 h'}[variable],
                'data_through': last.strftime('%Y-%m'), 'calibration_date': self.policy['calibration_date'],
                'computed_at': datetime.now(ZoneInfo('America/Costa_Rica')).isoformat(),
                'regional_only': True, 'model': policy['model'] if policy else None, 'rows': rows}
