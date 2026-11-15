"""Evidence card and export for ServiceResponse (J2.6). Owner: Jacky. [PROPUESTA].

Consumes the SAME snapshot the site shows (ServiceResponse or its jsonable dict). Nothing is
recalculated here: it only serializes. Pure stdlib, no I/O.

Conventions (also written to manifest.json): CSV UTF-8, comma, decimal point, "\\n" line ends,
missing value = empty cell, nested list/dict = compact JSON text, booleans true/false.
JSON is strict: null, never NaN/Infinity. generated_at and the hypothesis never change
result_id or the results.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from .contracts import ANALYSIS_VERSION, to_json, to_jsonable

CSV_CONVENTIONS = {
    "encoding": "utf-8", "delimiter": ",", "decimal": ".", "line_terminator": "\n",
    "missing": "empty cell", "nested": "compact JSON text", "booleans": "true/false",
    "row_keys": "every row carries result_id and product plus its join keys",
}
JOIN_KEY_COLUMNS = ("zone_id", "cell_id", "time", "year", "period", "valid_time", "indicator_id", "record_id")
EXPECTED_TABLES = {
    "historical": ("series.csv",), "event": ("event_series.csv",), "forecast": ("forecast.csv",),
    "water_distribution": ("water_distribution.csv", "water_records.csv"),
    "service_coverage": ("service_coverage.csv",), "capabilities": (), "data_coverage": (),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _label(r: dict) -> str:
    if r["source_mode"] in (None, "unknown") or r["synthetic"] is None:
        return "Origen desconocido: no presentable como real."
    if r["synthetic"] is True:
        return "Datos sinteticos de contrato (mock): no son evidencia cientifica."
    return "Datos reales."


def presentable_as_real(r: dict) -> bool:
    return r["source_mode"] == "real" and r["synthetic"] is False


def _summary(r: dict) -> str:
    """Deterministic template over the available fields only; never invents a number."""
    av, p = r["availability"], r["payload"]
    if av["status"] in ("unavailable", "unsupported", "error") or p is None:
        text = f"Sin resultado ({av['status']}: {av['reason_code']}). {av['message']}"
    else:
        prod, q = r["product"], r["query_effective"] or {}
        win = f"{q.get('start_date')}..{q.get('end_date')}"
        if prod == "historical" and isinstance(p, dict):
            per = p["period"]
            text = (f"Mapa de {len(p['cells'])} celdas, metrica {q.get('metric') or 'slope'}, "
                    f"anios {per['start_year']}-{per['end_year']}, correccion {p['correction']['method']}.")
        elif prod == "historical":
            text = f"Serie {q.get('variable')} {q.get('time_resolution')} {win}: {len(p)} registros."
        elif prod == "event":
            nulls = sum(1 for x in p if x["anomaly"] is None)
            anom = "no disponible (baseline insuficiente)" if nulls else "disponible"
            text = f"Episodio {q.get('event_id')} {win}: {len(p)} meses; anomalia {anom}. Descriptivo."
        elif prod == "forecast":
            fm = r["forecast_metadata"] or {}
            text = (f"Pronostico {fm.get('target_variable')} zona {fm.get('zone_id')}: {len(p)} puntos {win}; "
                    f"validacion {fm.get('validation_status')}.")
        elif prod == "water_distribution":
            states = sorted({x["report_state"] for x in p["periods"]})
            text = f"Registros de agua: {len(p['periods'])} periodos; estados {', '.join(states)}."
        elif prod == "service_coverage":
            inds = p["indicators"]
            nov = sum(1 for i in inds if i["value"] is None)
            text = f"Indicadores de servicio: {len(inds)}; {nov} sin valor (ver reason_code)."
        else:
            text = f"Resultado de {prod}."
    if av["status"] == "partial":
        text += f" Cobertura parcial: {av['message']}"
    if av["status"] == "stale":
        text += " Vencido: no tratar como actual."
    return f"{text} {_label(r)}"


def build_evidence_card_ext(resp: Any, hypothesis: str = "", generated_at: str | None = None) -> dict:
    r = to_jsonable(resp)
    prov = r["provenance"] or {}
    return {
        "schema_version": r["schema_version"],
        "result_id": r["result_id"],
        "preset_id": r["query_requested"].get("preset_id"),
        "hypothesis": hypothesis,
        "query": r["query_requested"],
        "query_effective": r["query_effective"],
        "product": r["product"],
        "availability": r["availability"],
        "source_mode": r["source_mode"],
        "synthetic": r["synthetic"],
        "presentable_as_real": presentable_as_real(r),
        "summary": _summary(r),
        "results": r["payload"],
        "warnings": r["warnings"],
        "limitations": r["limitations"],
        "source_ids": prov.get("source_ids", []),
        "data_sha256": prov.get("data_sha256"),
        "mask_version": prov.get("mask_version"),
        "analysis_version": ANALYSIS_VERSION,
        "generated_at": generated_at or _now(),
        "geographic_context": r["geographic_context"],
        "data_coverage": r["data_coverage"],
        "forecast_metadata": r["forecast_metadata"],
        "distribution_metadata": r["distribution_metadata"],
        "service_coverage_metadata": r["service_coverage_metadata"],
    }


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return str(v)


def _csv(rows: list[dict], result_id: Any, product: str, extra: dict | None = None) -> tuple[bytes, list[str]]:
    lead = {"result_id": result_id, "product": product, **(extra or {})}
    cols: list[str] = list(lead)
    for row in rows:
        for k in row:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for row in rows:
        merged = {**lead, **row}
        w.writerow([_cell(merged.get(c)) for c in cols])
    return buf.getvalue().encode("utf-8"), cols


def _tables(r: dict) -> dict[str, list[dict]]:
    """Payload -> {csv name: rows}. Empty or null payloads yield no table (never an empty CSV)."""
    p, prod = r["payload"], r["product"]
    if p is None:
        return {}
    if prod == "historical":
        if isinstance(p, dict):
            rows = [{**c, "period_start_year": p["period"]["start_year"], "period_end_year": p["period"]["end_year"],
                     "family_id": (p["correction"]["family"] or {}).get("family_id"),
                     "correction_method": p["correction"]["method"]} for c in p["cells"]]
            return {"cells.csv": rows}
        return {"series.csv": p}
    if prod == "event":
        return {"event_series.csv": p}
    if prod == "forecast":
        fid = (r["forecast_metadata"] or {}).get("forecast_id")
        return {"forecast.csv": [{"forecast_id": fid, **x} for x in p]}
    if prod == "water_distribution":
        return {"water_distribution.csv": p["periods"], "water_records.csv": p["records"]}
    if prod == "service_coverage":
        return {"service_coverage.csv": p["indicators"]}
    return {}


def _expected(r: dict) -> tuple[str, ...]:
    if r["product"] == "historical" and r["query_requested"].get("metric"):
        return ("cells.csv",)
    return EXPECTED_TABLES.get(r["product"], ())


def _ficha(card: dict) -> str:
    av = card["availability"]
    lines = [f"# Ficha de evidencia: {card['product']}", "",
             f"- Resultado: `{card['result_id']}`",
             f"- Estado: **{av['status']}**" + (f" ({av['reason_code']})" if av["reason_code"] else ""),
             f"- Origen: `{card['source_mode']}`, sintetico: `{card['synthetic']}`, "
             f"presentable como real: `{card['presentable_as_real']}`",
             f"- Generada: {card['generated_at']}", "", "## Resumen", "", card["summary"], ""]
    if card["hypothesis"]:
        lines += ["## Hipotesis del usuario", "", card["hypothesis"],
                  "", "_La hipotesis no altera el calculo._", ""]
    lines += ["## Consulta", "", "```json", json.dumps(card["query"], ensure_ascii=False, indent=2), "```", ""]
    if card["query_effective"]:
        lines += ["Ventana efectiva: "
                  f"{card['query_effective'].get('start_date')}..{card['query_effective'].get('end_date')}", ""]
    if card["warnings"]:
        lines += ["## Advertencias", ""] + [f"- {w}" for w in card["warnings"]] + [""]
    lines += ["## Limitaciones", ""] + [f"- {x}" for x in card["limitations"]] + [""]
    lines += [f"data_sha256: `{card['data_sha256']}`  ", f"analysis_version: `{card['analysis_version']}`", ""]
    return "\n".join(lines)


def build_export(resp: Any, hypothesis: str = "", generated_at: str | None = None) -> dict[str, bytes]:
    """{filename: bytes}. manifest.json lists present and absent tables; no fake empty tables."""
    r = to_jsonable(resp)
    card = build_evidence_card_ext(r, hypothesis, generated_at)
    files: dict[str, bytes] = {}
    present, absent = [], []
    tables = {k: v for k, v in _tables(r).items() if v}
    for name, rows in tables.items():
        data, cols = _csv(rows, r["result_id"], r["product"])
        files[name] = data
        present.append({"table": name, "rows": len(rows), "columns": cols,
                        "join_keys": ["result_id"] + [c for c in JOIN_KEY_COLUMNS if c in cols]})
    av = r["availability"]
    for name in _expected(r):
        if name not in tables:
            absent.append({"table": name, "availability_status": av["status"],
                           "reason_code": av["reason_code"] if r["payload"] is None else "empty_payload",
                           "message": av["message"]})
    files["evidence.json"] = (to_json(card, indent=2) + "\n").encode("utf-8")
    if r["provenance"] is not None:
        files["provenance.json"] = (to_json(r["provenance"], indent=2) + "\n").encode("utf-8")
    files["ficha.md"] = _ficha(card).encode("utf-8")
    manifest = {
        "schema_version": r["schema_version"], "result_id": r["result_id"], "product": r["product"],
        "source_mode": r["source_mode"], "synthetic": r["synthetic"],
        "availability": {"status": av["status"], "reason_code": av["reason_code"]},
        "generated_at": card["generated_at"], "conventions": CSV_CONVENTIONS,
        "tables_present": present, "tables_absent": absent, "files": sorted(list(files) + ["manifest.json"]),
    }
    files["manifest.json"] = (to_json(manifest, indent=2) + "\n").encode("utf-8")
    return files
