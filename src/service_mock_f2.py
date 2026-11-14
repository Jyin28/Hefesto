"""Hefesto MOCK service, F2 part (J2.1 availability states, J2.3 catalog and queries).

Development tool ONLY: every output is synthetic=True, source_mode="mock". Values are
deterministic contract examples, not NASA data. Real service (src/service.py) must never
silently fall back to this module. Pure stdlib; no I/O at import.

Fixture zones trigger each availability state:
  CR_PN, CR_CAR     available
  MOCK_PN_NORTH     available, cells shared with CR_PN
  MOCK_PARTIAL      partial: data only 1981-2010
  MOCK_NODATA       unavailable: zone without cells or data
  MOCK_STALE        stale: snapshot past valid_until
  MOCK_ERROR        error: technical failure
unsupported: time_resolution="daily", wrong product for a function, unsupported map metric.
Malformed queries raise ValueError (never a fake success).
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone

from . import service_mock as base
from .contracts import (
    ANALYSIS_VERSION,
    ANNUAL_UNITS,
    COVERAGE_END_YEAR,
    COVERAGE_START_YEAR,
    MONTHLY_UNITS,
    PRESET_IDS,
    SLOPE_UNITS,
    STATS_CONFIG,
    VARIABLE_IDS,
    canonical_json,
    compute_result_id,
    sha256_hex,
    to_jsonable,
)
from .contracts_ext import (
    EXT_SCHEMA_VERSION,
    MAP_METRICS,
    PRODUCTS,
    SPATIAL_LEVELS,
    SUPPORTED_RESOLUTIONS,
    TIME_RESOLUTIONS,
    AnalysisQuery,
    Availability,
    CellSpec,
    ForecastMetadata,
    ForecastPoint,
    ServiceIndicator,
    ServiceResponse,
    WaterRecord,
    ZoneSpec,
    parse_date,
)

GRID_ID = "MOCK_GRID"
GRID_VERSION = "mock-1"
ZONE_VERSION = "mock-1"
NATIVE_RES = (0.5, 0.625)
COVERAGE = (date(COVERAGE_START_YEAR, 1, 1), date(COVERAGE_END_YEAR, 12, 31))
EVENTS = {"EL_NINO_1997_98": (date(1997, 6, 1), date(1998, 5, 31))}
DEFAULT_BASELINE = "1981-2010"
MIN_BASELINE_VALUES = 24  # plan s3: min values per reference month
STALE_VALID_UNTIL = "2024-06-30"
_SCALE = "Celdas de decenas de km (0,5 x 0,625 grados); no es limite administrativo ni detalle de finca."


@dataclass(frozen=True)
class _ZoneDef:
    label: str
    base: str  # region whose synthetic series the zone reuses
    cells: tuple[tuple[str, int], ...]  # (region, idx) into base._MOCK_CELLS
    range: tuple[date, date]
    state: str  # ok | nodata | stale | error


def _pn(*idx):
    return tuple(("CR_PN", i) for i in idx)


def _car(*idx):
    return tuple(("CR_CAR", i) for i in idx)


_ZONES = {
    "CR_PN": _ZoneDef("Sector Pacifico Norte (ventana didactica)", "CR_PN", _pn(0, 1, 2, 3, 4), COVERAGE, "ok"),
    "CR_CAR": _ZoneDef("Sector Caribe (ventana didactica)", "CR_CAR", _car(0, 1, 2, 3, 4), COVERAGE, "ok"),
    "MOCK_PN_NORTH": _ZoneDef("MOCK: norte de CR_PN (celdas compartidas)", "CR_PN", _pn(3, 4), COVERAGE, "ok"),
    "MOCK_PARTIAL": _ZoneDef("MOCK: zona con datos solo hasta 2010", "CR_CAR", _car(0, 1), (COVERAGE[0], date(2010, 12, 31)), "ok"),
    "MOCK_NODATA": _ZoneDef("MOCK: zona sin datos", "CR_PN", (), COVERAGE, "nodata"),
    "MOCK_STALE": _ZoneDef("MOCK: snapshot vencido", "CR_PN", _pn(0), COVERAGE, "stale"),
    "MOCK_ERROR": _ZoneDef("MOCK: fallo tecnico", "CR_PN", (), COVERAGE, "error"),
}


def _cell_id(region: str, idx: int) -> str:
    lat, lon = base._MOCK_CELLS[region][idx]
    return f"G_{lat:.3f}_{lon:.3f}"


_CELLS: dict[str, tuple[str, int]] = {
    _cell_id(r, i): (r, i) for r in base._MOCK_CELLS for i in range(len(base._MOCK_CELLS[r]))
}


def _footprint(lat: float, lon: float) -> tuple[float, float, float, float]:
    return (lon - NATIVE_RES[1] / 2, lat - NATIVE_RES[0] / 2, lon + NATIVE_RES[1] / 2, lat + NATIVE_RES[0] / 2)


def _zone_cells(zone_id: str) -> tuple[str, ...]:
    return tuple(_cell_id(r, i) for r, i in _ZONES[zone_id].cells)


def _zones_of_cell(cell_id: str) -> tuple[str, ...]:
    return tuple(z for z in _ZONES if cell_id in _zone_cells(z))


def _today() -> date:
    """Injectable clock: tests patch this to evaluate expiry independent of the real date."""
    return datetime.now(timezone.utc).date()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- catalog (J2.3)

def list_zones() -> list[ZoneSpec]:
    out = []
    for zid, z in _ZONES.items():
        pts = [base._MOCK_CELLS[r][i] for r, i in z.cells] or [base._MOCK_CELLS[z.base][0]]
        fps = [_footprint(lat, lon) for lat, lon in pts]
        bbox = (min(f[0] for f in fps), min(f[1] for f in fps), max(f[2] for f in fps), max(f[3] for f in fps))
        cells = _zone_cells(zid)
        kind = "didactic_box" if zid in ("CR_PN", "CR_CAR") else "mock_fixture"
        lim = [_SCALE, "Datos sinteticos de contrato; no son evidencia cientifica."]
        if kind == "mock_fixture":
            lim.append("Zona ficticia que existe solo para probar estados de disponibilidad.")
        out.append(ZoneSpec(
            zid, z.label, kind, bbox, "EPSG:4326", ZONE_VERSION,
            sha256_hex(canonical_json({"bbox": bbox})), base.MASK_VERSION,
            sha256_hex(canonical_json({"cells": cells})), cells, ("S1",), _SCALE, tuple(lim)))
    return out


def list_cells(zone_id: str | None = None) -> list[CellSpec]:
    if zone_id is not None and zone_id not in _ZONES:
        raise ValueError(f"zone_id invalido: {zone_id!r}. Validos: {', '.join(_ZONES)}.")
    ids = _zone_cells(zone_id) if zone_id else tuple(_CELLS)
    out = []
    for cid in ids:
        r, i = _CELLS[cid]
        lat, lon = base._MOCK_CELLS[r][i]
        out.append(CellSpec(cid, GRID_ID, GRID_VERSION, lat, lon, _footprint(lat, lon), NATIVE_RES,
                            ("S1",), _zones_of_cell(cid)))
    return out


# ---------------------------------------------------------------- validation

def validate_analysis_query(q: AnalysisQuery) -> None:
    """Malformed query -> readable ValueError. Valid-but-uncovered -> availability, not here."""
    if q.product not in PRODUCTS:
        raise ValueError(f"product invalido: {q.product!r}. Validos: {', '.join(PRODUCTS)}.")
    if q.spatial_level not in SPATIAL_LEVELS:
        raise ValueError(f"spatial_level invalido: {q.spatial_level!r}. Validos: {', '.join(SPATIAL_LEVELS)}.")
    if q.spatial_level == "zone":
        if not q.zone_ids or q.cell_ids:
            raise ValueError("spatial_level='zone' exige zone_ids no vacio y cell_ids vacio.")
    elif not q.cell_ids or q.zone_ids:
        raise ValueError("spatial_level='cell' exige cell_ids no vacio y zone_ids vacio.")
    for z in q.zone_ids:
        if z not in _ZONES:
            raise ValueError(f"zone_id invalido: {z!r}. Validos: {', '.join(_ZONES)}.")
    for c in q.cell_ids:
        if c not in _CELLS:
            raise ValueError(f"cell_id invalido: {c!r}. Use list_cells().")
    if q.product in ("historical", "event", "forecast") and q.variable not in VARIABLE_IDS:
        raise ValueError(f"variable invalida: {q.variable!r}. Validas: {', '.join(VARIABLE_IDS)}.")
    if q.variable is not None and q.variable not in VARIABLE_IDS:
        raise ValueError(f"variable invalida: {q.variable!r}. Validas: {', '.join(VARIABLE_IDS)}.")
    s, e = parse_date(q.start_date, "start_date"), parse_date(q.end_date, "end_date")
    if s > e:
        raise ValueError(f"Periodo invalido: start_date {q.start_date} > end_date {q.end_date}.")
    if q.time_resolution not in TIME_RESOLUTIONS:
        raise ValueError(f"time_resolution invalida: {q.time_resolution!r}. Validas: {', '.join(TIME_RESOLUTIONS)}.")
    if q.preset_id is not None and q.preset_id not in PRESET_IDS:
        raise ValueError(f"preset_id invalido: {q.preset_id!r}. Validos: {', '.join(PRESET_IDS)}.")
    if q.event_id is not None and q.event_id not in EVENTS:
        raise ValueError(f"event_id invalido: {q.event_id!r}. Validos: {', '.join(EVENTS)}.")
    if q.metric is not None and q.metric not in MAP_METRICS:
        raise ValueError(f"metric invalida: {q.metric!r}. Validas: {', '.join(MAP_METRICS)}.")
    if q.baseline is not None:
        _parse_baseline(q.baseline)


def _parse_baseline(text: str) -> tuple[int, int]:
    try:
        a, b = text.split("-")
        a, b = int(a), int(b)
    except (AttributeError, ValueError):
        raise ValueError(f"baseline debe ser 'YYYY-YYYY', recibido {text!r}.") from None
    if a > b:
        raise ValueError(f"baseline invalido: {text!r}.")
    return a, b


def _qdict(q: AnalysisQuery) -> dict:
    d = to_jsonable(q)
    return d


# ---------------------------------------------------------------- availability core

def _avail(status, reason, message, missing=(), rng=None, retry=False,
           res=SUPPORTED_RESOLUTIONS) -> Availability:
    return Availability(status, reason, message, tuple(missing),
                        None if rng is None else (rng[0].isoformat(), rng[1].isoformat()),
                        tuple(res), _now(), retry)


def _selection(q: AnalysisQuery):
    """(zone_ids, cell_ids, per-zone state map, data range) for a validated query."""
    if q.spatial_level == "cell":
        return (), tuple(dict.fromkeys(q.cell_ids)), {}, COVERAGE
    zones = tuple(dict.fromkeys(q.zone_ids))
    cells = tuple(dict.fromkeys(c for z in zones for c in _zone_cells(z)))
    states = {z: _ZONES[z].state for z in zones}
    live = [z for z in zones if states[z] in ("ok", "stale")]
    lo = max([_ZONES[z].range[0] for z in live], default=COVERAGE[0])
    hi = min([_ZONES[z].range[1] for z in live], default=COVERAGE[1])
    return zones, cells, states, (lo, hi)


def _resolve(q: AnalysisQuery):
    """Returns (availability, effective (start, end) | None, selection)."""
    sel = _selection(q)
    zones, cells, states, rng = sel
    s, e = parse_date(q.start_date, "start_date"), parse_date(q.end_date, "end_date")
    if q.time_resolution not in SUPPORTED_RESOLUTIONS:
        return (_avail("unsupported", "resolution_not_supported",
                       f"Resolucion {q.time_resolution!r} fuera del contrato; use monthly o annual."), None, sel)
    vals = list(states.values())
    if "error" in vals:
        return (_avail("error", "internal_error", "Fallo tecnico simulado al leer la zona.", retry=True), None, sel)
    if vals and all(v == "nodata" for v in vals):
        return (_avail("unavailable", "no_data_for_zone", "La zona no tiene datos ni celdas en el catalogo.",
                       ("zone_cells", "source_data")), None, sel)
    lo, hi = max(s, rng[0]), min(e, rng[1])
    if lo > hi:
        return (_avail("unavailable", "out_of_coverage",
                       f"Ventana fuera de la cobertura {rng[0]}..{rng[1]}.", ("data_in_window",), rng), None, sel)
    missing = [z for z, v in states.items() if v == "nodata"]
    if "stale" in vals:
        return (_avail("stale", "snapshot_expired",
                       f"Snapshot vencido (valid_until {STALE_VALID_UNTIL}); no tratar como actual.",
                       missing, rng, True), (lo, hi), sel)
    if missing or (lo, hi) != (s, e):
        reasons = []
        if missing:
            reasons.append("zones_without_data")
        if (lo, hi) != (s, e):
            reasons.append("window_truncated")
        return (_avail("partial", "+".join(reasons),
                       f"Cobertura parcial: efectivo {lo}..{hi}; faltan {missing or 'parte de la ventana'}.",
                       missing or ["data_in_window"], rng), (lo, hi), sel)
    return _avail("available", None, "Datos disponibles para la consulta.", (), rng), (lo, hi), sel


# ---------------------------------------------------------------- synthetic values

def _tilt(region: str, variable: str, idx: int, year: int) -> float:
    return 0.15 * (idx - 2) * abs(base._PARAMS[(region, variable)][1]) * (year - COVERAGE_START_YEAR)


def _annual_value(region, variable, idx, year):
    v = base._synthetic_value(region, variable, year)
    return round(v + (_tilt(region, variable, idx, year) if idx is not None else 0.0), 6)


def _monthly_value(region, variable, idx, year, month):
    annual = _annual_value(region, variable, idx, year)
    season = math.sin(2.0 * math.pi * (month - 1) / 12.0)
    nino = date(1997, 6, 1) <= date(year, month, 1) <= date(1998, 5, 1)
    if variable == "T2M":
        return round(annual + 1.5 * season + (0.8 if nino else 0.0), 6)
    days = 366.0 if calendar.isleap(year) else 365.0
    return round(annual / days * (1.0 + 0.6 * season) * (0.7 if nino and region == "CR_PN" else 1.0), 6)


def _units(q_var: str | None, level: str):
    return (MONTHLY_UNITS if level == "monthly" else ANNUAL_UNITS)[q_var]


def _months(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def _complete_years(start: date, end: date) -> tuple[int, int] | None:
    y0 = start.year if (start.month, start.day) == (1, 1) else start.year + 1
    y1 = end.year if (end.month, end.day) == (12, 31) else end.year - 1
    return (y0, y1) if y0 <= y1 else None


def _targets(sel, state_ok_only=True):
    """[(label_key, label, region, idx|None)] series sources for a selection."""
    zones, cells, states, _ = sel
    out = []
    if zones:
        for z in zones:
            if states[z] in ("ok", "stale"):
                out.append(("zone_id", z, _ZONES[z].base, None))
    else:
        for c in cells:
            r, i = _CELLS[c]
            out.append(("cell_id", c, r, i))
    return out


# ---------------------------------------------------------------- envelope

def _geo(sel) -> dict:
    zones, cells, _, _ = sel
    specs = {z.zone_id: z for z in list_zones()}
    return {
        "zones": [{"zone_id": z, "label": specs[z].label, "bbox": list(specs[z].bbox), "crs": specs[z].crs,
                   "zone_version": specs[z].zone_version, "geometry_sha256": specs[z].geometry_sha256,
                   "mask_version": specs[z].mask_version, "mask_sha256": specs[z].mask_sha256,
                   "cell_ids": list(specs[z].cell_ids)} for z in zones],
        "cell_ids": list(cells),
        "grid_id": GRID_ID, "grid_version": GRID_VERSION, "native_resolution_deg": list(NATIVE_RES),
        "geographic_scale": _SCALE,
        "scale_warning": "Una celda puede pertenecer a varias zonas; no sumar celdas compartidas dos veces.",
    }


def _coverage(q: AnalysisQuery, eff, rng) -> dict:
    s, e = parse_date(q.start_date, "start_date"), parse_date(q.end_date, "end_date")
    expected = len(list(_months(s, e)))
    if eff is None:
        return {"expected_months": expected, "valid_months": 0, "complete_years": 0,
                "missing_periods": [[s.isoformat(), e.isoformat()]], "available_range": None}
    lo, hi = eff
    valid = len(list(_months(lo, hi)))
    cy = _complete_years(lo, hi)
    missing = []
    if s < lo:
        missing.append([s.isoformat(), (lo.fromordinal(lo.toordinal() - 1)).isoformat()])
    if e > hi:
        missing.append([(hi.fromordinal(hi.toordinal() + 1)).isoformat(), e.isoformat()])
    return {"expected_months": expected, "valid_months": valid,
            "complete_years": 0 if cy is None else cy[1] - cy[0] + 1, "missing_periods": missing,
            "available_range": [rng[0].isoformat(), rng[1].isoformat()]}


def _provenance(payload_sha: str) -> dict:
    return {
        "provider": "MOCK (sintetico, no NASA)", "source_ids": ["S1"], "retrieved_at": None,
        "provider_version": None, "synthetic": True, "mask_version": base.MASK_VERSION,
        "data_sha256": payload_sha, "git_commit": None,
        "transformations": ["generador sintetico determinista"],
    }


def _respond(q: AnalysisQuery, product: str, avail: Availability, eff, sel, payload,
             warnings=(), effective_extra=None, keep_payload=False, forecast_metadata=None,
             distribution_metadata=None, service_coverage_metadata=None,
             coverage_range=None) -> ServiceResponse:
    """Build the common envelope. request_id is deterministic here (mock only)."""
    req = _qdict(q)
    request_id = "req-" + sha256_hex(canonical_json(req))[:12]
    usable = payload is not None and (keep_payload or avail.status in ("available", "partial", "stale"))
    qe = None
    if eff is not None:
        qe = {**req, "product": product, "start_date": eff[0].isoformat(), "end_date": eff[1].isoformat(),
              **(effective_extra or {})}
    sha = sha256_hex(canonical_json(payload)) if usable else None
    rng = coverage_range or sel[3]
    w = list(warnings) + ["synthetic"]
    if avail.status == "stale":
        w.append("snapshot_expired")
    return ServiceResponse(
        schema_version=EXT_SCHEMA_VERSION, request_id=request_id, product=product, query_requested=req,
        query_effective=qe,
        result_id=compute_result_id(qe, sha, base.MASK_VERSION) if usable and qe else None,
        availability=avail, source_mode="mock", synthetic=True,
        payload=payload if usable else None,
        provenance=_provenance(sha) if usable else None,
        geographic_context=_geo(sel), data_coverage=_coverage(q, eff, rng),
        limitations=("Datos sinteticos de contrato; no son evidencia cientifica.", _SCALE),
        warnings=tuple(dict.fromkeys(w)),
        forecast_metadata=forecast_metadata, distribution_metadata=distribution_metadata,
        service_coverage_metadata=service_coverage_metadata,
    )


def _prepare(q: AnalysisQuery, expected_product: str | None):
    validate_analysis_query(q)
    avail, eff, sel = _resolve(q)
    if expected_product is not None and q.product != expected_product:
        avail = _avail("unsupported", "wrong_product",
                       f"Esta funcion solo soporta product={expected_product!r}; recibido {q.product!r}.")
        eff = None
    return avail, eff, sel


# ---------------------------------------------------------------- queries (J2.3)

def _probe(q: AnalysisQuery, **over) -> AnalysisQuery:
    return AnalysisQuery(**{**q.__dict__, **over})


def get_capabilities(q: AnalysisQuery) -> ServiceResponse:
    """Per-product availability for the zone/cells/window so Kevin can enable options."""
    validate_analysis_query(q)
    caps = {}
    for p in PRODUCTS:
        if p == "forecast":
            probe = _probe(q, product=p, variable=q.variable or "T2M", start_date="2025-01-01",
                           end_date="2025-06-30")
            caps[p] = get_local_forecast(probe).availability
        elif p in ("water_distribution", "service_coverage"):
            probe = _probe(q, product=p, variable=None, start_date="2024-01-01", end_date="2024-06-30")
            fn = get_water_distribution if p == "water_distribution" else get_service_coverage
            caps[p] = fn(probe).availability
        else:
            probe = _probe(q, product=p, variable=q.variable or "T2M",
                           event_id="EL_NINO_1997_98" if p == "event" else q.event_id)
            if p == "event":
                probe = _probe(probe, start_date="1997-06-01", end_date="1998-05-31")
            caps[p], _, _ = _resolve(probe)
    return _respond(q, "capabilities", caps["historical"], None, _selection(q),
                    {k: to_jsonable(v) for k, v in caps.items()}, keep_payload=True)


def get_data_coverage(q: AnalysisQuery) -> ServiceResponse:
    """Data coverage (not water-service coverage): months, complete years, missing periods."""
    avail, eff, sel = _prepare(q, None)
    cov = _coverage(q, eff, sel[3])
    return _respond(q, "data_coverage", avail, eff, sel, cov if eff else None)


def get_series(q: AnalysisQuery) -> ServiceResponse:
    """Monthly or annual series per zone/cell. Gaps keep the real time axis; no filling."""
    avail, eff, sel = _prepare(q, "historical")
    if eff is None:
        return _respond(q, q.product, avail, None, sel, None)
    lo, hi = eff
    rows = []
    for key, label, region, idx in _targets(sel):
        if q.time_resolution == "monthly":
            for y, m in _months(lo, hi):
                rows.append({key: label, "variable": q.variable, "time": f"{y:04d}-{m:02d}-01",
                             "value": _monthly_value(region, q.variable, idx, y, m),
                             "unit": MONTHLY_UNITS[q.variable], "synthetic": True})
        else:
            for y in range(lo.year, hi.year + 1):
                mv = len([1 for yy, _ in _months(lo, hi) if yy == y])
                rows.append({key: label, "variable": q.variable, "year": y,
                             "value": _annual_value(region, q.variable, idx, y),
                             "unit": ANNUAL_UNITS[q.variable], "months_valid": mv,
                             "complete": mv == 12, "synthetic": True})
    return _respond(q, "historical", avail, eff, sel, rows)


def get_map(q: AnalysisQuery) -> ServiceResponse:
    """Per-cell map payload. Cells shared by several zones appear once (dedup by cell_id)."""
    avail, eff, sel = _prepare(q, "historical")
    metric = q.metric or "slope"
    if eff is not None and metric == "anomaly":
        avail, eff = _avail("unsupported", "metric_not_supported",
                            "La metrica 'anomaly' del mapa se sirve con product='event'."), None
    if eff is None:
        return _respond(q, q.product, avail, None, sel, None, effective_extra=None)
    cy = _complete_years(*eff)
    if cy is None:
        avail = _avail("unavailable", "no_complete_years", "La ventana efectiva no contiene anios completos.",
                       ("complete_years",), sel[3])
        return _respond(q, q.product, avail, None, sel, None)
    y0, y1 = cy
    cell_ids = [c for c in sel[1]]
    regions = {_CELLS[c][0] for c in cell_ids}
    trends = {}
    meta = None
    for r in sorted(regions):
        ts, meta = base.get_cell_trends(q.variable, r, y0, y1)
        for t in ts:
            trends[(t.lat, t.lon)] = t
    rows = []
    for cid in cell_ids:
        r, i = _CELLS[cid]
        lat, lon = base._MOCK_CELLS[r][i]
        t = trends[(lat, lon)]
        if metric == "slope":
            val, unit = t.slope_per_decade, SLOPE_UNITS[q.variable]
        elif metric == "q":
            val, unit = t.q_value, "probability"
        else:
            vals = [_annual_value(r, q.variable, i, y) for y in range(y0, y1 + 1)]
            val, unit = round(sum(vals) / len(vals), 6), ANNUAL_UNITS[q.variable]
        rows.append({"cell_id": cid, "lat": lat, "lon": lon, "footprint": list(_footprint(lat, lon)),
                     "metric": metric, "value": val, "unit": unit, "p_value": t.p_value,
                     "q_value": t.q_value, "significant": t.significant, "level": t.level,
                     "status": t.status, "n_years": t.n_years, "synthetic": True,
                     "zone_ids": list(_zones_of_cell(cid))})
    payload = {"cells": rows, "period": {"start_year": y0, "end_year": y1},
               "correction": {"method": "fdr_by", "family": meta}}
    w = [] if (y0, y1) == (eff[0].year, eff[1].year) else ["partial_years_excluded"]
    return _respond(q, "historical", avail, eff, sel, payload, w,
                    {"metric": metric})


def get_event_series(q: AnalysisQuery) -> ServiceResponse:
    """Monthly series of the episode with climatology/anomaly. Descriptive; not trend inference.

    Window is the event window (event_id required). Baseline defaults to 1981-2010 and needs
    >= 24 valid values per reference month; otherwise anomaly is null and the response is partial.
    """
    validate_analysis_query(q)
    if q.event_id is None and q.product == "event":
        raise ValueError("product='event' exige event_id.")
    if q.event_id is not None:
        s, e = EVENTS[q.event_id]
        q = AnalysisQuery(**{**q.__dict__, "start_date": s.isoformat(), "end_date": e.isoformat()})
    avail, eff, sel = _prepare(q, "event")
    if eff is None:
        return _respond(q, q.product, avail, None, sel, None)
    b0, b1 = _parse_baseline(q.baseline or DEFAULT_BASELINE)
    lo, hi = eff
    base_lo, base_hi = max(sel[3][0].year, b0), min(sel[3][1].year, b1)
    counts_per_month = max(0, base_hi - base_lo + 1)
    baseline_ok = counts_per_month >= MIN_BASELINE_VALUES
    warnings = []
    if not baseline_ok:
        avail = _avail("partial", "baseline_insufficient",
                       f"Baseline {b0}-{b1} con {counts_per_month} valores por mes (<{MIN_BASELINE_VALUES}): "
                       "anomalia no disponible.", ("baseline_valid_counts",), sel[3])
        warnings.append("baseline_insufficient")
    rows = []
    for key, label, region, idx in _targets(sel):
        clim = {}
        if baseline_ok:
            for m in range(1, 13):
                vals = [_monthly_value(region, q.variable, idx, y, m) for y in range(base_lo, base_hi + 1)]
                clim[m] = round(sum(vals) / len(vals), 6)
        for y, m in _months(lo, hi):
            v = _monthly_value(region, q.variable, idx, y, m)
            c = clim.get(m)
            rows.append({key: label, "variable": q.variable, "time": f"{y:04d}-{m:02d}-01", "value": v,
                         "unit": MONTHLY_UNITS[q.variable], "climatology": c,
                         "anomaly": None if c is None else round(v - c, 6),
                         "baseline": f"{base_lo}-{base_hi}",
                         "baseline_valid_counts": counts_per_month, "synthetic": True})
    return _respond(q, "event", avail, eff, sel, rows, warnings,
                    {"event_id": q.event_id, "baseline": f"{base_lo}-{base_hi}"})


# ---------------------------------------------------------------- forecast (J2.4)

FORECAST_RANGE = (date(2025, 1, 1), date(2025, 6, 30))
FORECAST_TZ = "America/Costa_Rica"
# zone -> (validation_status, valid_until). Zones absent here have no model at all.
_FORECAST_FIXTURES = {
    "CR_PN": ("validated", "2030-12-31"),
    "CR_CAR": ("not_evaluated", "2030-12-31"),
    "MOCK_PN_NORTH": ("failed", "2030-12-31"),
    "MOCK_STALE": ("validated", STALE_VALID_UNTIL),
}
_FORECAST_TARGET = {
    "T2M": "Temperatura media mensual del aire a 2 m",
    "PRECTOTCORR": "Tasa media mensual de precipitacion corregida",
}
_FORECAST_METRIC = {"T2M": ("MAE", 0.4, "degC"), "PRECTOTCORR": ("MAE", 0.8, "mm/day")}


def _forecast_metadata(zone_id: str, variable: str) -> ForecastMetadata:
    fx = _FORECAST_FIXTURES.get(zone_id)
    status, valid_until = fx if fx else ("not_evaluated", None)
    has_model = fx is not None
    evaluated = status in ("validated", "failed")
    name, val, unit = _FORECAST_METRIC[variable]
    cfg = {"zone": zone_id, "variable": variable, "model": "mock_fixture_v1"}
    return ForecastMetadata(
        forecast_id=f"FC_{zone_id}_{variable}_mock1", model_id="MOCK_FIXTURE" if has_model else None,
        model_version="mock-1" if has_model else None, target_variable=variable,
        target_definition=_FORECAST_TARGET[variable], unit=MONTHLY_UNITS[variable], zone_id=zone_id,
        effective_scale=_SCALE, issued_at="2025-01-01T00:00:00Z" if has_model else None,
        data_cutoff="2024-12-31" if has_model else None,
        training_start="1981-01-01" if has_model else None, training_end="2024-12-31" if has_model else None,
        forecast_start=FORECAST_RANGE[0].isoformat() if has_model else None,
        forecast_end=FORECAST_RANGE[1].isoformat() if has_model else None,
        horizon="6 months" if has_model else None, frequency="monthly" if has_model else None,
        timezone=FORECAST_TZ, valid_until=valid_until, input_source_ids=("S1",) if has_model else (),
        input_hashes=(sha256_hex(canonical_json(_zone_cells(zone_id))),) if has_model else (),
        config_hash=sha256_hex(canonical_json(cfg)) if has_model else None, code_version=ANALYSIS_VERSION,
        synthetic=True, generation_mode="imported", validation_status=status,
        validation_method="rolling_origin_mock" if evaluated else None,
        evaluation_period="2015-01..2024-12" if evaluated else None,
        sample_count=120 if evaluated else None,
        benchmark="climatologia mensual 1981-2010" if evaluated else None,
        metric_name=name if evaluated else None,
        metric_value=(val if status == "validated" else round(val * 6, 6)) if evaluated else None,
        metric_unit=unit if evaluated else None,
        limitations=("Puntos sinteticos de un generador, no la salida de un modelo.",
                     "No es un pronostico meteorologico ni de suministro."),
    )


def get_local_forecast(q: AnalysisQuery) -> ServiceResponse:
    """Forecast for ONE zone. Never extrapolates the historical trend as a substitute model.

    Without a validated model the response is unavailable with a reason; metadata stays
    present so the UI can explain why. Expiry is evaluated at query time via _today().
    """
    validate_analysis_query(q)
    sel = _selection(q)

    def out(avail, eff=None, payload=None, meta=None, warnings=(), extra=None):
        return _respond(q, q.product, avail, eff, sel, payload, warnings, extra,
                        forecast_metadata=to_jsonable(meta) if meta else None,
                        coverage_range=FORECAST_RANGE)

    res = ("monthly",)
    if q.product != "forecast":
        return out(_avail("unsupported", "wrong_product",
                          f"Esta funcion solo soporta product='forecast'; recibido {q.product!r}.", res=res))
    if q.spatial_level == "cell":
        return out(_avail("unsupported", "forecast_cell_not_supported",
                          "El pronostico se ofrece por zona, no por celda.", res=res))
    if q.time_resolution == "daily":
        return out(_avail("unsupported", "resolution_not_supported",
                          "El pronostico es mensual; 'daily' esta fuera del contrato.", res=res))
    if len(sel[0]) != 1:
        return out(_avail("unsupported", "forecast_single_zone_only",
                          "El pronostico exige exactamente una zona.", res=res))
    zone = sel[0][0]
    if _ZONES[zone].state == "error":
        return out(_avail("error", "internal_error", "Fallo tecnico simulado al leer el pronostico.",
                          retry=True, res=res))
    meta = _forecast_metadata(zone, q.variable)
    fx = _FORECAST_FIXTURES.get(zone)
    if fx is None:
        return out(_avail("unavailable", "no_forecast_model", "No hay modelo de pronostico para la zona.",
                          ("forecast_model",), res=res), meta=meta)
    if fx[0] == "not_evaluated":
        return out(_avail("unavailable", "forecast_not_validated",
                          "El modelo existe pero aun no esta validado; no se presenta como prediccion.",
                          ("forecast_validation",), FORECAST_RANGE, res=res), meta=meta)
    if fx[0] == "failed":
        return out(_avail("unavailable", "forecast_validation_failed",
                          "El modelo no supero la validacion frente al benchmark.",
                          ("forecast_validation",), FORECAST_RANGE, res=res), meta=meta)
    s, e = parse_date(q.start_date, "start_date"), parse_date(q.end_date, "end_date")
    lo, hi = max(s, FORECAST_RANGE[0]), min(e, FORECAST_RANGE[1])
    if lo > hi:
        return out(_avail("unavailable", "out_of_forecast_range",
                          f"Ventana fuera del horizonte {FORECAST_RANGE[0]}..{FORECAST_RANGE[1]}.",
                          ("forecast_in_window",), FORECAST_RANGE, res=res), meta=meta)
    has_interval = q.variable == "T2M"
    points = []
    for y, m in _months(lo, hi):
        v = _monthly_value(_ZONES[zone].base, q.variable, None, y, m)
        points.append(ForecastPoint(f"{y:04d}-{m:02d}-01", v, round(v - 0.6, 6) if has_interval else None,
                                    round(v + 0.6, 6) if has_interval else None,
                                    0.8 if has_interval else None,
                                    "mock_fixed_width" if has_interval else None))
    warnings = [] if has_interval else ["interval_not_estimated"]
    extra = {"forecast_id": meta.forecast_id}
    if _today() > date.fromisoformat(fx[1]):
        avail = _avail("stale", "forecast_expired", f"Pronostico vencido (valid_until {fx[1]}).", (),
                       FORECAST_RANGE, True, res)
    elif (lo, hi) != (s, e):
        avail = _avail("partial", "window_truncated", f"Horizonte efectivo {lo}..{hi}.",
                       ("forecast_in_window",), FORECAST_RANGE, False, res)
    else:
        avail = _avail("available", None, "Pronostico disponible y validado.", (), FORECAST_RANGE, False, res)
    return out(avail, (lo, hi), [to_jsonable(p) for p in points], meta, warnings, extra)


# ---------------------------------------------------------------- water (J2.4)

WATER_RANGE = (date(2024, 1, 1), date(2024, 6, 30))
WATER_DATASET = "mock-water-1"
WATER_TZ = "America/Costa_Rica"
_SERVICE_AREA = {"CR_PN": "SA_PN_01", "CR_CAR": "SA_CAR_01"}
# service area -> (target households, denominator source). CR_CAR has no denominator.
_TARGET_HOUSEHOLDS = {"SA_PN_01": (12000, "MOCK_PADRON_2024"), "SA_CAR_01": (None, None)}
_SCHED_VOLUME = {"CR_PN": 120000.0, "CR_CAR": 90000.0}
_SCHED_HOURS = 360.0
_BASE_HOUSEHOLDS = {"CR_PN": 12000, "CR_CAR": 9000}
# month -> (observed factor, corrected factor | None, event_status); None = no report
_WATER_MONTHS = {1: (0.95, None, "delivered"), 2: (0.96, None, "delivered"),
                 3: (0.90, 0.975, "delivered"), 4: (0.0, None, "paused"), 5: None,
                 6: (1.10, None, "delivered")}
_INDICATOR_DEFS = {
    "household_coverage": "hogares unicos atendidos / hogares objetivo del mismo territorio y periodo x100",
    "volume_compliance": "volumen observado / volumen programado x100",
    "continuity": "horas efectivas de servicio / horas esperadas x100",
    "report_completeness": "reportes recibidos / reportes esperados x100 (calidad documental, no suministro)",
}


def _month_bounds(y: int, m: int) -> tuple[str, str]:
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


def _water_records(zone_id: str) -> list[WaterRecord]:
    area = _SERVICE_AREA[zone_id]
    sched, hh = _SCHED_VOLUME[zone_id], _BASE_HOUSEHOLDS[zone_id]
    out = []

    def rec(rid, y, m, kind, status, vol, hours, households, compl, flags=(), corrects=None, sup=None):
        a, b = _month_bounds(y, m)
        return WaterRecord(rid, "MOCK_WATER", WATER_DATASET, zone_id, area, ZONE_VERSION, a, b, WATER_TZ,
                           kind, status, vol, "m3", households, None, hours, compl, "2024-07-05T00:00:00Z",
                           None, tuple(flags), True, corrects, sup)

    for m in range(1, 7):
        y = 2024
        key = f"W_{zone_id}_{y}{m:02d}"
        out.append(rec(f"{key}_s", y, m, "scheduled", "scheduled", sched, _SCHED_HOURS, None, None))
        spec = _WATER_MONTHS[m]
        if spec is None:
            continue  # month without report: no observed record at all
        f, fc, status = spec
        if fc is not None:  # original observed is kept and marked superseded, never deleted
            out.append(rec(f"{key}_o", y, m, "observed", status, round(sched * f, 6), _SCHED_HOURS * f,
                           round(hh * f), 1.0, ("superseded",), None, f"{key}_c"))
            out.append(rec(f"{key}_c", y, m, "corrected", status, round(sched * fc, 6), _SCHED_HOURS * fc,
                           round(hh * fc), 1.0, (), f"{key}_o", None))
        else:
            out.append(rec(f"{key}_o", y, m, "observed", status, round(sched * f, 6), _SCHED_HOURS * f,
                           round(hh * f), 1.0))
    return out


def _water_periods(zone_id: str, months) -> list[dict]:
    recs = _water_records(zone_id)
    rows = []
    for y, m in months:
        key = f"{y:04d}-{m:02d}"
        if not (WATER_RANGE[0] <= date(y, m, 1) <= WATER_RANGE[1]):
            continue
        in_month = [r for r in recs if r.period_start.startswith(key)]
        sched = next(r for r in in_month if r.record_kind == "scheduled")
        obs = next((r for r in in_month if r.record_kind != "scheduled" and r.superseded_by is None), None)
        if obs is None:
            state = "not_reported"
        else:
            state = "paused" if obs.event_status == "paused" else "reported"
        rows.append({"zone_id": zone_id, "service_area_id": sched.service_area_id, "period": key,
                     "scheduled_volume": sched.volume, "observed_volume": None if obs is None else obs.volume,
                     "volume_unit": "m3", "report_state": state, "scheduled_record_id": sched.record_id,
                     "observed_record_id": None if obs is None else obs.record_id,
                     "_sched": sched, "_obs": obs})
    return rows


def _water_context(q: AnalysisQuery, product: str):
    """Shared validation/resolution. Returns (availability, effective|None, selection, ok_zones)."""
    validate_analysis_query(q)
    if q.variable is not None:
        raise ValueError("variable no aplica a productos de agua; use variable=None.")
    sel = _selection(q)
    res = ("monthly",)
    if q.product != product:
        return (_avail("unsupported", "wrong_product",
                       f"Esta funcion solo soporta product={product!r}; recibido {q.product!r}.", res=res),
                None, sel, [])
    if q.spatial_level == "cell":
        return (_avail("unsupported", "water_cell_not_supported",
                       "Los productos de agua se ofrecen por zona/area de servicio, no por celda.", res=res),
                None, sel, [])
    if q.time_resolution == "daily":
        return (_avail("unsupported", "resolution_not_supported",
                       "Los registros de agua son mensuales; 'daily' esta fuera del contrato.", res=res),
                None, sel, [])
    zones, _, states, _ = sel
    if "error" in states.values():
        return (_avail("error", "internal_error", "Fallo tecnico simulado al leer registros de agua.",
                       retry=True, res=res), None, sel, [])
    ok = [z for z in zones if z in _SERVICE_AREA]
    missing = [z for z in zones if z not in _SERVICE_AREA]
    if not ok:
        return (_avail("unavailable", "no_water_records", "No hay registros de agua para la zona.",
                       ("water_records",), res=res), None, sel, [])
    s, e = parse_date(q.start_date, "start_date"), parse_date(q.end_date, "end_date")
    lo, hi = max(s, WATER_RANGE[0]), min(e, WATER_RANGE[1])
    if lo > hi:
        return (_avail("unavailable", "out_of_water_range",
                       f"Ventana fuera de los registros {WATER_RANGE[0]}..{WATER_RANGE[1]}.",
                       ("water_records_in_window",), WATER_RANGE, res=res), None, sel, ok)
    reasons = []
    if missing:
        reasons.append("zones_without_records")
    if (lo, hi) != (s, e):
        reasons.append("window_truncated")
    if reasons:
        return (_avail("partial", "+".join(reasons), f"Registros parciales: efectivo {lo}..{hi}.",
                       missing or ["water_records_in_window"], WATER_RANGE, res=res), (lo, hi), sel, ok)
    return (_avail("available", None, "Registros de agua disponibles.", (), WATER_RANGE, res=res),
            (lo, hi), sel, ok)


def _dist_meta(zones_ok) -> dict:
    return {
        "dataset_version": WATER_DATASET,
        "crosswalk": {"version": "mock-1", "method": "identity (zona == area de servicio)",
                      "zones": {z: _SERVICE_AREA[z] for z in zones_ok}},
        "note": "Planificado no equivale a entregado; pausa registrada, cero observado y sin reporte son estados distintos.",
    }


def get_water_distribution(q: AnalysisQuery) -> ServiceResponse:
    """Scheduled vs observed water records per zone/month, with versioned corrections."""
    avail, eff, sel, ok = _water_context(q, "water_distribution")
    if eff is None:
        return _respond(q, q.product, avail, None, sel, None, coverage_range=WATER_RANGE)
    records, periods = [], []
    for z in ok:
        records.extend(_water_records(z))
        periods.extend(_water_periods(z, _months(*eff)))
    keep = {p["period"] for p in periods}
    records = [r for r in records if r.period_start[:7] in keep]
    for p in periods:
        p.pop("_sched"), p.pop("_obs")
    payload = {"records": [to_jsonable(r) for r in records], "periods": periods}
    return _respond(q, "water_distribution", avail, eff, sel, payload,
                    distribution_metadata=_dist_meta(ok), coverage_range=WATER_RANGE)


def _pct(num, den):
    """(value, reason). Never invents a value: missing/zero denominator -> None."""
    if num is None:
        return None, "not_reported"
    if den is None:
        return None, "denominator_missing"
    if den == 0:
        return None, "denominator_zero"
    return round(100.0 * num / den, 6), None


def _indicators(zone_id: str, row: dict) -> list[ServiceIndicator]:
    sched, obs = row["_sched"], row["_obs"]
    area = row["service_area_id"]
    target, source = _TARGET_HOUSEHOLDS[area]
    paused = row["report_state"] == "paused"
    specs = [
        ("volume_compliance", None if obs is None else obs.volume, sched.volume, "m3", "m3", None, None),
        ("continuity", None if obs is None else obs.service_duration_hours, sched.service_duration_hours,
         "h", "h", None, None),
        ("household_coverage", None if obs is None else obs.households_served, target, "households",
         "households", source, "mock: un registro por area-mes; no se suman hogares entre meses"),
    ]
    out = []
    for iid, n, d, nu, du, dsrc, dedup in specs:
        v, reason = _pct(n, d)
        flags = []
        if v is not None and v > 100:
            flags.append("exceeds_100")  # kept as-is: never clipped to hide an inconsistency
        if paused:
            flags.append("paused")
        out.append(ServiceIndicator(iid, _INDICATOR_DEFS[iid], row["period"], zone_id, area, n, d, nu, du, v,
                                    "percent", dsrc, dedup, tuple(flags), reason))
    received = 0 if obs is None else 1
    out.append(ServiceIndicator("report_completeness", _INDICATOR_DEFS["report_completeness"], row["period"],
                                zone_id, area, float(received), 1.0, "reports", "reports",
                                float(received) * 100.0, "percent", None, None, (), None))
    return out


def get_service_coverage(q: AnalysisQuery) -> ServiceResponse:
    """Water-service indicators computed only from compatible numerators/denominators.

    Not derived from rainfall or climate coverage. Percentages are never averaged across zones.
    """
    avail, eff, sel, ok = _water_context(q, "service_coverage")
    if eff is None:
        return _respond(q, q.product, avail, None, sel, None, coverage_range=WATER_RANGE)
    inds, not_reported = [], False
    for z in ok:
        for row in _water_periods(z, _months(*eff)):
            not_reported |= row["report_state"] == "not_reported"
            inds.extend(_indicators(z, row))
    warnings = []
    if len(ok) > 1:
        warnings.append("no_cross_zone_average")
    if not_reported:
        warnings.append("months_not_reported")
    if any(i.reason_code == "denominator_missing" for i in inds) and avail.status == "available":
        avail = _avail("partial", "denominator_missing", "Falta denominador para algun indicador.",
                       ("household_denominator",), WATER_RANGE, res=("monthly",))
    meta = {"definitions": _INDICATOR_DEFS,
            "denominator_sources": {_SERVICE_AREA[z]: _TARGET_HOUSEHOLDS[_SERVICE_AREA[z]][1] for z in ok},
            "cross_zone_average": None, "crosswalk_version": "mock-1"}
    return _respond(q, "service_coverage", avail, eff, sel, {"indicators": [to_jsonable(i) for i in inds]},
                    warnings, service_coverage_metadata=meta, coverage_range=WATER_RANGE)


# ---------------------------------------------------------------- cache hooks (J2.5)
# The adapter, not the store, knows which versions identify its inputs. src/snapshots.py is
# provider-agnostic and receives these functions as hooks.

def normalize_query(q: AnalysisQuery) -> AnalysisQuery:
    """Canonical form for cache identity: sorted unique ids; event window and baseline filled in."""
    over = {"zone_ids": tuple(sorted(dict.fromkeys(q.zone_ids))),
            "cell_ids": tuple(sorted(dict.fromkeys(q.cell_ids)))}
    if q.event_id is not None:
        s, e = EVENTS[q.event_id]
        over.update(start_date=s.isoformat(), end_date=e.isoformat())
    if q.product == "event" or q.event_id is not None:
        over["baseline"] = q.baseline or DEFAULT_BASELINE
    return AnalysisQuery(**{**q.__dict__, **over})


def input_manifest(q: AnalysisQuery) -> dict:
    """Versions of every input that can change the result, known BEFORE computing it.

    Sections are selected per product by snapshots.KEY_PARTS. generated_at, checked_at and the
    hypothesis are deliberately absent: they never alter the analysis.
    """
    validate_analysis_query(q)
    specs = {z.zone_id: z for z in list_zones()}
    zones = sorted(dict.fromkeys(q.zone_ids))
    man = {
        "source_mode": "mock",
        "schema": EXT_SCHEMA_VERSION,
        "code": ANALYSIS_VERSION,
        "method": sha256_hex(canonical_json(STATS_CONFIG)),
        "geo": {"zones": {z: {"zone_version": specs[z].zone_version,
                              "geometry_sha256": specs[z].geometry_sha256,
                              "mask_sha256": specs[z].mask_sha256} for z in zones},
                "cells": sorted(dict.fromkeys(q.cell_ids)), "grid_version": GRID_VERSION},
        # whole family, not just the selected view: changing the universe changes identity
        "family_data": sha256_hex(canonical_json({f"{r}|{v}": list(p) for (r, v), p in base._PARAMS.items()})),
    }
    if q.product == "event":
        man["event"] = {"event_id": q.event_id, "baseline": q.baseline or DEFAULT_BASELINE,
                        "temporal_support": "monthly"}
    if q.product == "forecast" and q.spatial_level == "zone" and len(zones) == 1 and q.variable:
        fm = _forecast_metadata(zones[0], q.variable)
        man["forecast"] = {k: getattr(fm, k) for k in ("model_id", "model_version", "config_hash", "issued_at",
                                                       "data_cutoff", "horizon", "validation_status")}
    if q.product in ("water_distribution", "service_coverage"):
        in_scope = [z for z in zones if z in _SERVICE_AREA]
        recs = [r for z in in_scope for r in _water_records(z)]
        man["water"] = {"dataset_version": WATER_DATASET,
                        "corrections": sorted(r.record_id for r in recs
                                              if r.superseded_by or r.corrects_record_id)}
        man["crosswalk"] = {"version": "mock-1", "zones": {z: _SERVICE_AREA[z] for z in in_scope}}
    if q.product == "service_coverage":
        man["indicator_definition"] = sha256_hex(canonical_json(_INDICATOR_DEFS))
        man["denominator"] = {_SERVICE_AREA[z]: list(_TARGET_HOUSEHOLDS[_SERVICE_AREA[z]])
                              for z in zones if z in _SERVICE_AREA}
    return man


def refresh_freshness(resp: dict) -> dict:
    """Re-evaluate expiry of a cached forecast at read time without touching issued_at or payload."""
    import copy
    out = copy.deepcopy(resp)
    fm = out.get("forecast_metadata")
    av = out.get("availability")
    if fm and fm.get("valid_until") and av and av["status"] in ("available", "partial") \
            and _today() > date.fromisoformat(fm["valid_until"]):
        av["status"], av["reason_code"] = "stale", "forecast_expired"
        av["message"] = f"Pronostico vencido (valid_until {fm['valid_until']})."
        av["retryable"] = True
        av["checked_at"] = _now()
        out["warnings"] = list(dict.fromkeys(list(out.get("warnings", [])) + ["snapshot_expired"]))
    return out
