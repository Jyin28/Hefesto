"""Predicciones del sitio: pronóstico regional experimental + contexto de El Niño, escrito como JSON estático.

El cálculo lo hace `hefesto_forecast` (motor del paquete de predicciones, con sus límites de horizonte y calibración).
Este módulo solo lo llama, agrega lo que el motor no hace (episodio de El Niño en curso, años análogos) y guarda
`web/public/data/predicciones.json`, que lee la página «Predicciones». Así el sitio sigue siendo estático.

Qué NO hace, a propósito (ver `docs/predicciones.md`):
  * No predice el inicio de un Niño con un modelo dinámico: el episodio en curso sale de RONI y el rango de fechas de su
    fin es una comparación con episodios fuertes anteriores («análogos»), no un pronóstico.
  * No publica lluvia, humedad ni UV como pronóstico: el motor solo da referencia histórica y los análogos de El Niño
    son descriptivos (qué pasó otras veces), con pocos años.
  * No genera nada por cantón: todo es regional (Costa Rica, Pacífico Norte, Caribe).

Uso (desde la raíz de Hefesto):
    python -m src.predictions
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `hefesto_forecast` vive en la raíz del repo, junto a `src` y `web`
    sys.path.insert(0, str(ROOT))

from hefesto_forecast.engine import ForecastEngine  # noqa: E402

OUTPUT = ROOT / "web" / "public" / "data" / "predicciones.json"
REGIONS = ("CR", "CR_PN", "CR_CAR")
REGION_NAMES = {"CR": "Costa Rica (promedio nacional)", "CR_PN": "Pacífico Norte (Guanacaste)", "CR_CAR": "Caribe (Limón)"}
STRONG_PEAK = 1.5        # un episodio «fuerte» llega a RONI >= 1,5
MIN_EPISODE_MONTHS = 5   # NOAA: 5 meses seguidos con RONI >= 0,5
ANALOG_RONI = 1.0        # años análogos: RONI de septiembre >= 1,0 (moderado o más fuerte)
ANALOG_MIN_YEARS = 5     # con menos años no se publica un análogo


def month_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m")


def add_months(ts: pd.Timestamp, months: int) -> pd.Timestamp:
    return ts + pd.DateOffset(months=int(round(months)))


def month_diff(a: pd.Timestamp, b: pd.Timestamp) -> int:
    """Meses de `a` a `b` (b - a)."""
    return (b.year - a.year) * 12 + b.month - a.month


def category(value: float) -> str:
    """Categorías ONI de NOAA aplicadas a RONI, según el pico alcanzado."""
    if value >= 2.0:
        return "muy fuerte"
    if value >= 1.5:
        return "fuerte"
    if value >= 1.0:
        return "moderado"
    return "débil"


# --- El Niño: episodios y análogos ---

def find_episodes(roni: pd.Series) -> list[dict]:
    """Rachas de al menos 5 meses seguidos con RONI >= 0,5. La última puede seguir abierta (episodio en curso)."""
    episodes: list[dict] = []
    start = previous = None
    for ts, value in roni.items():
        if value >= 0.5 and start is None:
            start = ts
        if value < 0.5 and start is not None:
            episodes.append({"start": start, "end": previous, "open": False})
            start = None
        previous = ts
    if start is not None:
        episodes.append({"start": start, "end": roni.index[-1], "open": True})
    found = []
    for episode in episodes:
        months = month_diff(episode["start"], episode["end"]) + 1
        if months < MIN_EPISODE_MONTHS:
            continue
        segment = roni.loc[episode["start"]:episode["end"]]
        found.append({**episode, "months": months, "peak": float(segment.max()), "peak_month": segment.idxmax()})
    return found


def enso_block(roni: pd.Series) -> dict:
    episodes = find_episodes(roni)
    latest_ts = roni.index[-1]
    current = next((e for e in episodes if e["open"]), None)
    done = [e for e in episodes if not e["open"]]
    history = [{"start": month_label(e["start"]), "end": month_label(e["end"]), "months": e["months"],
                "peak": round(e["peak"], 1), "peak_month": month_label(e["peak_month"])} for e in done]
    block: dict = {
        "status": "active" if current else "none", "history": history,
        "latest": {"month": month_label(latest_ts), "value": round(float(roni.iloc[-1]), 1)},
        "series": [{"month": month_label(ts), "value": round(float(v), 1)} for ts, v in roni.loc["2023-01":].items()],
        "definition": "Episodio de El Niño: RONI ≥ 0,5 durante al menos 5 meses seguidos (NOAA).",
    }
    if not current:
        return block
    strong = [e for e in done if e["peak"] >= STRONG_PEAK]
    months_so_far = current["months"]
    # Duración total de los episodios fuertes que ya terminaron, descartando los más cortos que lo ya transcurrido.
    durations = np.array([e["months"] for e in strong if e["months"] >= months_so_far], dtype=float)
    # Cuántos meses después del inicio llegó el pico (solo los que lo alcanzaron en el mes actual o después).
    peak_offsets = np.array([month_diff(e["start"], e["peak_month"]) for e in strong
                             if month_diff(e["start"], e["peak_month"]) >= months_so_far - 1], dtype=float)
    start = current["start"]
    block.update({
        "start": month_label(start), "months_so_far": months_so_far,
        "peak_so_far": {"month": month_label(current["peak_month"]), "value": round(current["peak"], 1)},
        "category": category(current["peak"]),
        "rising": bool(roni.iloc[-1] >= current["peak"] - 1e-9),
    })
    if len(durations) >= ANALOG_MIN_YEARS:
        low, mid, high = (float(np.percentile(durations, q)) for q in (10, 50, 90))
        # La duración cuenta meses desde el inicio: un episodio de n meses termina n-1 meses después del primero.
        end = {key: month_label(add_months(start, value - 1)) for key, value in (("earliest", low), ("typical", mid), ("latest", high))}
        block["analog"] = {
            "basis": f"Episodios fuertes anteriores (pico de RONI ≥ {STRONG_PEAK:g}) que duraron al menos {months_so_far} meses.",
            "n": int(len(durations)),
            "events": [{"start": month_label(e["start"]), "end": month_label(e["end"]), "months": e["months"], "peak": round(e["peak"], 1)}
                       for e in strong if e["months"] >= months_so_far],
            "duration_months": {"p10": round(low, 1), "median": round(mid, 1), "p90": round(high, 1),
                                "min": int(durations.min()), "max": int(durations.max())},
            "end_window": end,
        }
        if len(peak_offsets) >= ANALOG_MIN_YEARS:
            block["analog"]["peak_window"] = {
                "earliest": month_label(add_months(start, np.percentile(peak_offsets, 10))),
                "typical": month_label(add_months(start, np.percentile(peak_offsets, 50))),
                "latest": month_label(add_months(start, np.percentile(peak_offsets, 90))),
                "n": int(len(peak_offsets)),
            }
    return block


def rain_analog(monthly_mm: pd.Series, roni: pd.Series, base_year: int, targets: list[pd.Timestamp]) -> dict | None:
    """Qué llovió en los meses `targets` en los años en que, como ahora, RONI de septiembre era >= 1,0.

    Es descriptivo: pocos años y sin prueba de significancia. No es un pronóstico.
    """
    analog_years = [year for year in range(monthly_mm.index[0].year, base_year)
                    if pd.Timestamp(year, 9, 1) in roni.index and roni[pd.Timestamp(year, 9, 1)] >= ANALOG_RONI]
    if len(analog_years) < ANALOG_MIN_YEARS:
        return None
    ref = monthly_mm.loc["1991-01":"2020-12"]
    months = []
    for target in targets:
        shift = target.year - base_year  # 0 para diciembre del año base, 1 para enero..mayo siguientes
        values = [monthly_mm.get(pd.Timestamp(year + shift, target.month, 1)) for year in analog_years]
        values = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
        sample = ref[ref.index.month == target.month]
        if len(values) < ANALOG_MIN_YEARS:
            continue
        months.append({"month": month_label(target), "n_years": int(len(values)), "mean_mm": round(float(values.mean()), 1),
                       "reference_mean_mm": round(float(sample.mean()), 1),
                       "anomaly_pct": round(100 * (float(values.mean()) / float(sample.mean()) - 1), 1),
                       "share_above_median": round(float((values > sample.median()).mean()), 2),
                       "share_above_100mm": round(float((values >= 100).mean()), 2)})
    return {"criterion": f"Años con RONI de septiembre ≥ {ANALOG_RONI:g}", "years": analog_years, "months": months}


# --- Ensamble ---

def build(engine: ForecastEngine | None = None, now: datetime | None = None) -> dict:
    engine = engine or ForecastEngine()
    now = now or datetime.now(ZoneInfo("America/Costa_Rica"))
    default_start = (pd.Timestamp(now.year, now.month, 1) + pd.DateOffset(months=1)).strftime("%Y-%m")
    start = max(default_start, engine.policy["first_target"])
    variables: dict = {}
    for variable in ("T2M", "PRECTOTCORR", "RH2M", "UV"):
        regions = {}
        for region in REGIONS:
            result = engine.forecast(region, variable, start, 6)
            regions[region] = {"model": result["model"], "rows": result["rows"]}
            unit, source, data_through = result["unit"], result["source"], result["data_through"]
        variables[variable] = {"unit": unit, "source": source, "data_through": data_through, "regions": regions}

    roni = engine.roni
    base_year = pd.Timestamp(start + "-01").year if int(start[5:]) >= 9 else pd.Timestamp(start + "-01").year - 1
    targets = list(pd.date_range(start + "-01", periods=6, freq="MS"))
    analog: dict = {}
    for region in REGIONS:
        d = engine.frame[(engine.frame.source == "CDS") & (engine.frame.region == region) & (engine.frame.variable == "PRECTOTCORR")]
        series = pd.Series(d.value.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(d.date)))
        result = rain_analog(series * series.index.days_in_month, roni, base_year, targets)
        if result:
            analog[region] = result
    policy = {key: {"model": value["model"], "max_contiguous_horizon": value["max_contiguous_horizon"],
                    "horizons": {h: {k: v for k, v in info.items() if k in ("test_skill", "coverage90_recent", "skill_uncertain", "skill_ci95")}
                                 for h, info in value["horizons"].items() if int(h) <= value["max_contiguous_horizon"]}}
              for key, value in engine.policy["series"].items() if key.endswith("/T2M")}
    payload = {
        "schema": 1, "generated_at": now.isoformat(), "forecast_start": start,
        "calibration_date": engine.policy["calibration_date"],
        "data_through": variables["T2M"]["data_through"], "roni_through": month_label(roni.index[-1]),
        "region_names": REGION_NAMES, "enso": enso_block(roni), "variables": variables,
        "rain_analog": analog, "temperature_validation": policy,
        "limits": [
            "Todo es regional (Costa Rica, Pacífico Norte y Caribe): no hay predicciones por cantón, celda ni ASADA.",
            "Solo la temperatura tiene pronóstico experimental, y solo para los primeros meses: la validación no justifica más.",
            "Lluvia, humedad y UV son referencias históricas; los años análogos de El Niño son descriptivos, con pocos años.",
            "El rango de fechas de El Niño compara con episodios fuertes anteriores; no es un modelo dinámico del océano.",
            "Sin validación contra estaciones locales. No usar para decidir racionamientos ni otras acciones operativas.",
        ],
    }
    return payload


def write(payload: dict, target: Path = OUTPUT) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def main() -> int:
    payload = build()
    write(payload)
    enso = payload["enso"]
    print(f"Predicciones escritas en {OUTPUT} (datos hasta {payload['data_through']}, RONI hasta {payload['roni_through']}).")
    if enso["status"] == "active":
        window = enso.get("analog", {}).get("end_window", {})
        print(f"El Niño en curso desde {enso['start']} ({enso['category']}); fin esperado {window.get('earliest')} a {window.get('latest')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
