"""Evidence card payload and CSV tables shared by the app and the API."""
import csv
from hashlib import sha256
from io import StringIO

from .contracts import to_json
from .web_data import climate, local_catalog


def evidence_card(region, variable, *, canton=None, **query):
    payload = climate(region, variable, **query)
    local = local_catalog()
    if canton is not None and (len(canton) != 3 or not canton.isascii() or not canton.isdecimal()):
        raise ValueError("El código cantonal debe tener tres dígitos")
    # When there is no selected canton, use the corresponding demo canton.
    if canton is None:
        canton = next((code for code, item in local["cantons"].items()
                       if item.get("regionId") == region), None)
    payload["cantonCode"] = canton
    payload["water_coverage"] = [
        row for row in local["waterCoverage"]
        if variable == "PRECTOTCORR" and row["cantonCode"] == canton
    ]
    payload["distribution"] = [
        row for row in local["distribution"] if variable == "PRECTOTCORR" and row["cantonCode"] == canton
    ]
    payload["water_operators"] = [
        row for row in local["operators"] if variable == "PRECTOTCORR" and canton in row["cantonCodes"]
    ]
    payload["water_sources"] = {
        key: value for key, value in local["sources"].items()
        if any(row.get("sourceId") == key
               for row in payload["water_coverage"] + payload["distribution"] + payload["water_operators"])
    }
    identity = {
        "schema_version": payload["schema_version"], "region": region, "variable": variable,
        "cell": payload["cellId"], "canton": canton, "comparison": payload["comparison"],
        "trend": payload["trend"], "enso": payload["enso"], "forecast": payload["forecast"],
        "raw_files": payload["provenance"]["raw_files"], "mask_version": payload["provenance"]["mask_version"],
        "water": payload["water_coverage"], "distribution": payload["distribution"],
        "water_operators": payload["water_operators"],
    }
    payload["result_id"] = "dt-" + sha256(to_json(identity, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return payload


def csv_tables(card):
    result_id = card["result_id"]
    selection = {"result_id": result_id, "region_id": card["regionId"],
                 "cell_id": card["cellId"], "variable": card["variable"]}
    window = {key: card["trend"][key] for key in ("start_year", "end_year")}
    series = [
        dict(row, **selection, **window, status="complete" if row["complete"] else "incomplete",
             source_id="nasa-power")
        for row in card["series"]
    ]
    comparison = card["comparison"]
    results = [dict(selection, **window, **{
        key: value for key, value in card["trend"].items() if key not in ("region_id", "variable", *window)
        and not isinstance(value, (list, dict))
    }, source_id="nasa-power")]
    mk = card["evidence"]["mann_kendall"]
    results.append(dict(selection, **window, **{key: value for key, value in mk.items()
                                                if not isinstance(value, (list, dict))},
                        source_id="nasa-power"))
    if comparison:
        for label in ("window_a", "window_b"):
            data = comparison[label]
            results.append(dict(selection, window=label, start_year=data["start_year"],
                                end_year=data["end_year"], n_years=data["n_years"],
                                mean=data["mean"], slope_per_decade=data["slope_per_decade"],
                                status=data["status"], unit=data["unit"], source_id="nasa-power"))
        results.append(dict(selection, window="B−A", mean=comparison["mean_diff_b_minus_a"],
                            slope_per_decade=comparison["slope_diff_b_minus_a"],
                            unit=comparison["window_a"]["unit"], source_id="nasa-power"))
    provenance = card["provenance"]
    raw_file = next(entry for entry in provenance["raw_files"] if f"_{card['variable']}_" in entry["path"])
    source_rows = [{"source_id": "nasa-power", "label": card["source"], "url": card["sourceUrl"],
                    "raw_file": raw_file["path"], "sha256": raw_file["sha256"],
                    "retrieved_at": provenance["retrieved_at"], "api_version": provenance["api_version"],
                    "mask_version": provenance["mask_version"],
                    "limits": " | ".join(card["limitations"])}]
    source_rows.extend(dict(entry, source_id=key) for key, entry in card["water_sources"].items())
    event_sources = card["enso"].get("episode", {}).get("sources", []) + card["enso"].get("neutral_sources", [])
    source_rows.extend({"source_id": f"imn-{index}", "label": "Boletín IMN", "url": url}
                       for index, url in enumerate(event_sources, 1))
    return {
        "series": series, "results": results,
        "water": [dict(row, result_id=result_id, source_id=row["sourceId"]) for row in card["water_coverage"]],
        "distribution": [dict(row, result_id=result_id, source_id=row["sourceId"]) for row in card["distribution"]],
        "sources": [dict(row, result_id=result_id) for row in source_rows],
        "enso": [dict(row, **selection, unit=card["enso"]["unit"], source_id="nasa-power")
                 for row in card["enso"]["months"]],
    }


def format_csv(rows):
    stream = StringIO(newline="")
    columns = list(dict.fromkeys(key for row in rows for key in row))
    if columns:
        writer = csv.DictWriter(stream, columns)
        writer.writeheader()
        writer.writerows(rows)
    return stream.getvalue()


# --------------------------------------------------------------------------- #
# ExportBundle v2 (plan §4.7): UI = CSV = JSON, todos desde la MISMA ficha del servicio
# --------------------------------------------------------------------------- #
def _flat(row):
    return {k: (";".join(v) if isinstance(v, (list, tuple)) else v) for k, v in row.items()}


def _fmt_p(p):
    return "N/D" if p is None else ("<0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ","))


def _num(x, nd=3):
    return "N/D" if x is None else f"{x:.{nd}f}".replace(".", ",")


def evidence_markdown(card) -> str:
    from .service import WARNING_TEXT, _sector

    q = card["query"]
    lines = [
        f"# Ficha de detective — {card['preset_id']}",
        "",
        f"- **result_id:** `{card['result_id']}`",
        f"- **Período:** {q['start_year']}–{q['end_year']} · **Variable:** {q['variable']}",
        f"- **Datos sintéticos:** {'SÍ' if card['synthetic'] else 'no (NASA POWER real)'}",
        f"- **Generada:** {card['generated_at']} · **Análisis:** v{card['analysis_version']} · "
        f"**Máscara:** {card['mask_version']}",
        "",
        "## Hipótesis",
        card["hypothesis"] or "_(sin hipótesis)_",
        "",
        "## Resultado",
        card["summary"],
        "",
        "## Tendencias por sector",
        "| Sector | Pendiente/década | Cambio total | IC 95 % individual | p | p ajustado (BY) | Nivel | Años |",
        "|---|---:|---:|---|---:|---:|---|---:|",
    ]
    for r in card["results"]:
        ci = "N/D" if r["ci_low"] is None else f"[{_num(r['ci_low'])}, {_num(r['ci_high'])}]"
        lines.append(f"| {_sector(r['region_id'])} | {_num(r['slope_per_decade'])} {r['slope_unit']} | "
                     f"{_num(r['total_change'])} | {ci} | {_fmt_p(r['p_value'])} | {_fmt_p(r['p_adjusted'])} | "
                     f"{r['level']} | {r['n_years']} |")
    lines += ["", "## Familias de corrección (Benjamini–Yekutieli)"]
    for f in card["family_metadata"]:
        lines.append(f"- `{f['family_id']}` · {f['scope']} · pruebas planeadas {f['planned_tests']}, "
                     f"válidas {f['valid_tests']}, α = {f['alpha']}")
    lines += ["", "## Advertencias"]
    for w in card["warnings"]:
        lines.append(f"- **{w}:** {WARNING_TEXT.get(w, '')}")
    lines += ["", "## Límites"]
    lines += [f"- {text}" for text in card.get("provenance", {}).get("limitations", [])]
    lines += ["", "## Fuentes", "- S1 NASA POWER Monthly API: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/",
              "- S2 NASA POWER fuentes meteorológicas: https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/",
              "- S3 statsmodels HAC: https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html",
              "- S4 statsmodels multipletests: https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html",
              "", f"_SHA-256 de datos:_ `{card['data_sha256']}`", ""]
    return "\n".join(lines)


def build_export_bundle(card):
    from .contracts import ExportBundle

    series = [dict(r, result_id=card["result_id"]) for r in card["series"]]
    trends = []
    for r in card["results"]:
        diag = (card.get("diagnostics") or {}).get(r["region_id"], {})
        trends.append(_flat(dict(r, result_id=card["result_id"], mask_version=card["mask_version"],
                                 hac_sensitivity_changes_conclusion=diag.get("hac_sensitivity_changes_conclusion"))))
    return ExportBundle(
        series_csv=format_csv(series).encode("utf-8"),
        trends_csv=format_csv(trends).encode("utf-8"),
        provenance_json=to_json(card["provenance"], indent=2).encode("utf-8"),
        evidence_md=evidence_markdown(card).encode("utf-8"),
        evidence_json=to_json(card, indent=2).encode("utf-8"),
    )
