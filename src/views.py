"""Vistas Streamlit/Plotly de AguaAlerta. La UI NO calcula pendientes ni p: solo presenta
lo que devuelve el servicio (`service.build_evidence_card` y funciones hermanas).

Todo el mapa es Plotly puro con rectángulos de celdas nativas: no usa teselas ni topojson externos.
"""
from __future__ import annotations

from typing import Any

import plotly.colors as pc
import plotly.graph_objects as go
import streamlit as st

SECTOR_NAMES = {"CR_PN": "Pacífico Norte", "CR_CAR": "Caribe"}
SECTOR_COLORS = {"CR_PN": "#0EA5E9", "CR_CAR": "#10B981"}
VAR_NAMES = {"T2M": "Temperatura del aire a 2 m", "PRECTOTCORR": "Precipitación corregida"}
CELL_HALF = (0.25, 0.3125)  # medio ancho nativo (lat, lon)
WARNING_TEXT = {
    "short_record": "Serie corta: no se evalúa significancia.",
    "short_for_inference": "Menos de 30 años consecutivos: solo magnitud descriptiva.",
    "temporal_gaps": "Años faltantes dentro de la ventana: pendiente descriptiva, sin inferencia.",
    "incomplete_years": "Algunos años no están completos y no se usaron.",
    "degenerate_series": "Serie sin variación suficiente: no se puede estimar p ni intervalo.",
    "coverage_failure": "Cobertura espacial menor al 80 %: dato insuficiente.",
    "no_data": "Sin datos en la ventana.",
    "possible_inhomogeneity": "Se detectó un salto de nivel (posible cambio de fuente o de régimen).",
    "reanalysis_precip_caution": (
        "La lluvia de reanálisis no está validada con estaciones; NASA POWER documenta que los datos recientes "
        "pueden provenir de GEOS-IT sin normalización por pluviómetros. Úsela como patrón del producto, "
        "no como lluvia observada."),
    "coarse_resolution": "Celdas de decenas de km: no representan fincas, cantones ni cuencas.",
    "synthetic": "Datos sintéticos de desarrollo.",
}


def fmt_p(p: float | None) -> str:
    if p is None:
        return "N/D"
    return "<0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ",")


def fmt_num(x: float | None, nd: int = 3, unit: str = "") -> str:
    if x is None:
        return "N/D"
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",") + (f" {unit}" if unit else "")


def significance_label(r: dict) -> tuple[str, str]:
    """Distingue 'no evaluable' (None) de 'no significativo' (False)."""
    if r["status"] == "insufficient_data" or r["level"] == "none":
        return "⚪ No evaluable", "Registro insuficiente (menos de 10 años) o cobertura <80 %."
    if r["level"] == "descriptive":
        return "🟡 Solo descriptivo", "Menos de 30 años consecutivos o huecos: se muestra la magnitud, sin inferencia."
    if r["significant"] is True:
        return "🟢 Evidencia de cambio lineal", "p ajustado (BY) < 0,05 en la familia completa."
    if r["significant"] is False:
        return "🟠 Evidencia insuficiente", "No significa 'no cambia': significa que los datos no bastan para afirmarlo."
    return "⚪ No evaluable", "Sin p calculable."


# --------------------------------------------------------------------------- #
# Tarjetas de respuesta
# --------------------------------------------------------------------------- #
def render_cards(card: dict) -> None:
    q, results = card["query"], card["results"]
    variable = q["variable"]
    st.subheader("Respuesta en cuatro tarjetas")
    c1, c2, c3, c4 = st.columns(4)
    with c1.container(border=True):
        st.markdown("**1 · ¿Qué cambia?**")
        st.write(VAR_NAMES[variable])
        for r in results:
            slope = r["slope_per_decade"]
            arrow = "sin pendiente" if slope is None else ("↑ sube" if slope > 0 else "↓ baja" if slope < 0 else "→ estable")
            st.write(f"{SECTOR_NAMES[r['region_id']]}: **{arrow}**")
    with c2.container(border=True):
        st.markdown("**2 · ¿Dónde?**")
        for r in results:
            st.write(f"{SECTOR_NAMES[r['region_id']]} · {r['n_years']} años usados")
        st.caption("Sectores didácticos de celdas de ~55×69 km; no son límites administrativos.")
    with c3.container(border=True):
        st.markdown("**3 · ¿Cuánto?**")
        for r in results:
            ci = "" if r["ci_low"] is None else f" · IC95 % [{fmt_num(r['ci_low'], 2)}, {fmt_num(r['ci_high'], 2)}]"
            st.write(f"{SECTOR_NAMES[r['region_id']]}: **{fmt_num(r['slope_per_decade'], 2)}** {r['slope_unit']}{ci}")
            st.caption(f"Cambio total ajustado: {fmt_num(r['total_change'], 2)}")
    with c4.container(border=True):
        st.markdown("**4 · ¿Qué evidencia?**")
        for r in results:
            label, why = significance_label(r)
            st.write(f"{SECTOR_NAMES[r['region_id']]}: {label}")
            st.caption(f"p = {fmt_p(r['p_value'])} · p ajustado BY = {fmt_p(r['p_adjusted'])} · {why}")
    st.info(card["summary"])
    if "reanalysis_precip_caution" in card["warnings"]:
        st.warning(WARNING_TEXT["reanalysis_precip_caution"])


# --------------------------------------------------------------------------- #
# Series anuales
# --------------------------------------------------------------------------- #
def render_annual(card: dict) -> None:
    variable = card["query"]["variable"]
    unit = next((r["unit"] for r in card["series"]), "")
    fig = go.Figure()
    for r in card["results"]:
        region = r["region_id"]
        rows = [s for s in card["series"] if s["region_id"] == region]
        years = [s["year"] for s in rows]
        values = [s["value"] for s in rows]  # None → hueco visible, sin interpolar
        fig.add_trace(go.Scatter(x=years, y=values, mode="lines+markers", name=SECTOR_NAMES[region],
                                 line=dict(color=SECTOR_COLORS[region]), connectgaps=False))
        used = [(y, v) for y, v in zip(years, values) if v is not None]
        if r["slope_per_decade"] is not None and used:
            xbar = sum(y for y, _ in used) / len(used)
            ybar = sum(v for _, v in used) / len(used)
            b = r["slope_per_decade"] / 10.0  # la recta OLS pasa por (x̄, ȳ)
            fig.add_trace(go.Scatter(
                x=[r["first_used_year"], r["last_used_year"]],
                y=[ybar + b * (r["first_used_year"] - xbar), ybar + b * (r["last_used_year"] - xbar)],
                mode="lines", name=f"Ajuste {SECTOR_NAMES[region]}", line=dict(color=SECTOR_COLORS[region], dash="dash")))
    fig.update_layout(title=f"{VAR_NAMES[variable]} anual ({unit})", xaxis_title="Año", yaxis_title=unit,
                      height=430, legend=dict(orientation="h", y=-0.2), margin=dict(t=50, b=10))
    st.plotly_chart(fig, width="stretch")
    incomplete = [s for s in card["series"] if not s["complete"]]
    if incomplete:
        st.warning(f"{len(incomplete)} años incompletos (sin valor anual). No se interpolan.")
    st.caption("Línea punteada: ajuste lineal de la ficha. Un ciclo estacional o una anomalía no son una tendencia.")


# --------------------------------------------------------------------------- #
# Mensual / estacionalidad / anomalías
# --------------------------------------------------------------------------- #
def render_monthly(service: Any, card: dict) -> None:
    q = card["query"]
    if not hasattr(service, "get_monthly_view"):
        st.info("La vista mensual requiere el servicio real.")
        return
    fig_c, fig_a = go.Figure(), go.Figure()
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    unit = ""
    for region in q["regions"]:
        rows = service.get_monthly_view(q["variable"], region, q["start_year"], q["end_year"])
        unit = rows[0]["unit"] if rows else unit
        clim = {r["month"]: r["climatology"] for r in rows}
        fig_c.add_trace(go.Scatter(x=months, y=[clim.get(m) for m in range(1, 13)], mode="lines+markers",
                                   name=SECTOR_NAMES[region], line=dict(color=SECTOR_COLORS[region])))
        fig_a.add_trace(go.Bar(x=[r["time"] for r in rows], y=[r["anomaly"] for r in rows],
                               name=SECTOR_NAMES[region], marker_color=SECTOR_COLORS[region]))
    fig_c.update_layout(title=f"Ciclo estacional medio 1981–2010 ({unit})", height=340, margin=dict(t=50, b=10))
    fig_a.update_layout(title=f"Anomalía mensual vs. mismo mes de 1981–2010 ({unit})", barmode="group",
                        height=340, margin=dict(t=50, b=10))
    st.plotly_chart(fig_c, width="stretch")
    st.plotly_chart(fig_a, width="stretch")
    st.caption("Vista para aprender: el ciclo y las anomalías mensuales NO son tendencias multidecadales. "
               "La referencia exige ≥24 de 30 años por mes.")


# --------------------------------------------------------------------------- #
# Mapa por celda nativa (sin teselas externas)
# --------------------------------------------------------------------------- #
def render_map(service: Any, card: dict) -> None:
    q = card["query"]
    cells, meta = [], None
    for region in q["regions"]:
        c, meta = service.get_cell_trends(q["variable"], region, q["start_year"], q["end_year"])
        cells += c
    slopes = [c.slope_per_decade for c in cells if c.slope_per_decade is not None]
    if not slopes:
        st.info("Sin celdas evaluables.")
        return
    bound = max(abs(s) for s in slopes) or 1.0
    scale = "RdBu_r" if q["variable"] == "T2M" else "BrBG"
    fig = go.Figure()
    for c in cells:
        lat_h, lon_h = CELL_HALF
        if c.slope_per_decade is None:
            color = "#cccccc"
        else:
            color = pc.sample_colorscale(scale, [0.5 + 0.5 * c.slope_per_decade / bound])[0]
        fig.add_shape(type="rect", x0=c.lon - lon_h, x1=c.lon + lon_h, y0=c.lat - lat_h, y1=c.lat + lat_h,
                      fillcolor=color, line=dict(color="#222" if c.significant else "#888",
                                                 width=3 if c.significant else 1), opacity=0.9)
    fig.add_trace(go.Scatter(
        x=[c.lon for c in cells], y=[c.lat for c in cells], mode="markers+text",
        text=["✱" if c.significant else "" for c in cells], textposition="middle center",
        marker=dict(size=14, opacity=0.01, color="#000"), showlegend=False,
        hovertext=[f"{SECTOR_NAMES[c.region_id]} · celda ({c.lat:g}, {c.lon:g})<br>pendiente {fmt_num(c.slope_per_decade, 3)} "
                   f"{c.slope_unit}<br>p {fmt_p(c.p_value)} · q (BY) {fmt_p(c.q_value)}<br>nivel {c.level}" for c in cells],
        hoverinfo="text"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(
        colorscale=scale, cmin=-bound, cmax=bound, color=[0], showscale=True,
        colorbar=dict(title=cells[0].slope_unit)), showlegend=False))
    lons = [c.lon for c in cells]
    lats = [c.lat for c in cells]
    fig.update_xaxes(title="Longitud", range=[min(lons) - 0.5, max(lons) + 0.5])
    fig.update_yaxes(title="Latitud", range=[min(lats) - 0.45, max(lats) + 0.45], scaleanchor="x")
    fig.update_layout(height=520, title=f"Pendiente por celda nativa · {q['start_year']}–{q['end_year']}",
                      margin=dict(t=50, b=10), plot_bgcolor="#f4f4f4")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"✱ y borde grueso: q < 0,05 en la familia de {meta['planned_tests']} celdas de AMBOS sectores "
               f"({meta['family_id']}). Cada rectángulo es una celda nativa (~0,5° × 0,625°); no hay interpolación. "
               "La corrección no cambia al ocultar un sector.")
    table = [{"Sector": SECTOR_NAMES[c.region_id], "lat": c.lat, "lon": c.lon,
              f"Pendiente ({c.slope_unit})": c.slope_per_decade, "p": c.p_value, "q (BY)": c.q_value,
              "Significativa": {True: "sí", False: "no", None: "N/D"}[c.significant], "Años": c.n_years}
             for c in cells]
    st.dataframe(table, width="stretch", hide_index=True)


# --------------------------------------------------------------------------- #
# Comparación de sectores
# --------------------------------------------------------------------------- #
def render_comparison(card: dict) -> None:
    rows = []
    for r in card["results"]:
        label, _ = significance_label(r)
        rows.append({
            "Sector": SECTOR_NAMES[r["region_id"]], "Pendiente/década": r["slope_per_decade"],
            "Unidad": r["slope_unit"], "Cambio total": r["total_change"], "IC95 % inferior": r["ci_low"],
            "IC95 % superior": r["ci_high"], "p": r["p_value"], "p ajustado BY": r["p_adjusted"],
            "Lectura": label, "Nivel": r["level"], "Años": r["n_years"], "Método": r["method"],
        })
    st.dataframe(rows, width="stretch", hide_index=True)
    fam = card["family_metadata"][0]
    st.caption(f"Familia regional `{fam['family_id']}`: {fam['planned_tests']} pruebas planeadas "
               f"(2 variables × 2 sectores), {fam['valid_tests']} válidas, BY a α = {fam['alpha']}. "
               "Resultado exploratorio: la corrección no cubre todas las búsquedas de la sesión.")
    st.caption("No se elige sector, variable ni período para conseguir p < 0,05.")


# --------------------------------------------------------------------------- #
# ENOS
# --------------------------------------------------------------------------- #
def render_event(service: Any, card: dict) -> None:
    if not hasattr(service, "get_event_view"):
        st.info("Disponible solo con el servicio real.")
        return
    try:
        rows = service.get_event_view(card["query"]["variable"])
    except NotImplementedError:
        st.info("Vista de episodio no disponible en este modo.")
        return
    if not rows:
        st.info("Sin episodio disponible.")
        return
    fig = go.Figure()
    for region in card["query"]["regions"]:
        part = [r for r in rows if r["region_id"] == region]
        fig.add_trace(go.Bar(x=[r["time"][:7] for r in part], y=[r["anomaly"] for r in part],
                             name=SECTOR_NAMES[region], marker_color=SECTOR_COLORS[region]))
    fig.update_layout(title=f"Episodio ENOS jun 1997 – may 1998: anomalía mensual ({rows[0]['unit']})",
                      barmode="group", height=380, margin=dict(t=50, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Descriptivo: anomalía frente al mismo mes de 1981–2010. No es tendencia ni prueba de causa. "
               "ENOS puede modular de modo distinto las lluvias del Pacífico y del Caribe (UCR, S5) pero depende "
               "de época y región; esto no certifica signos opuestos. Contraparte neutral: sin verificar.")


# --------------------------------------------------------------------------- #
# Diagnósticos
# --------------------------------------------------------------------------- #
def render_diagnostics(card: dict) -> None:
    diagnostics = card.get("diagnostics")
    if not diagnostics:
        st.info("Diagnósticos disponibles solo con el servicio real.")
        return
    for region, d in diagnostics.items():
        st.markdown(f"#### {SECTOR_NAMES[region]}")
        sens = d["hac_sensitivity"]
        if sens:
            table = [{"Rezagos HAC": d["hac_main_lags"], "Rol": "principal (decisión explícita)"}]
            st.write("**Sensibilidad HAC** (nunca se elige el rezago favorable):")
            st.dataframe(
                [{"Rezagos HAC": f"L={d['hac_main_lags']} (principal)", "IC95 % inferior": None, "IC95 % superior": None,
                  "p": next((r["p_value"] for r in card["results"] if r["region_id"] == region), None)}]
                + [{"Rezagos HAC": f"L={s['lags']} (sensibilidad)", "IC95 % inferior": s["ci_low"],
                    "IC95 % superior": s["ci_high"], "p": s["p_value"]} for s in sens],
                hide_index=True, width="stretch")
            changed = d["hac_sensitivity_changes_conclusion"]
            if changed is True:
                st.warning("La conclusión (p < 0,05) cambia con otro rezago: resultado frágil.")
            elif changed is False:
                st.success("La conclusión no cambia con L = 1 o L = 5.")
        else:
            st.caption("Sin inferencia HAC (serie corta o con huecos).")
        h = d["homogeneity"]
        if h["status"] == "ok":
            flag = "posible salto de nivel" if h["possible_inhomogeneity"] else "sin salto de nivel detectado"
            st.write(f"**Homogeneidad (Pettitt sobre residuos)**: {flag} · año del posible cambio {h['break_year']} · "
                     f"p = {fmt_p(h['p_value'])}. Es un diagnóstico de calidad de datos; no modifica la tendencia.")
        mk = d["mann_kendall"]
        if mk["p_value"] is not None:
            st.write(f"**Contraste Sen + Mann–Kendall**: {fmt_num(mk['slope_per_decade'], 3)} {mk['slope_unit']}, "
                     f"p = {fmt_p(mk['p_value'])}, p ajustado = {fmt_p(mk['p_adjusted'])}. Solo contraste; no sustituye al OLS+HAC.")


# --------------------------------------------------------------------------- #
# Límites y descargas
# --------------------------------------------------------------------------- #
def render_limits(card: dict, rule: dict | None) -> None:
    prov = card.get("provenance", {})
    st.markdown("**Qué NO mide / límites**")
    items = list(prov.get("limitations", []))
    if rule:
        items = list(rule.get("not_measured", [])) + items
    for item in dict.fromkeys(items):
        st.write(f"- {item}")
    st.markdown("**Advertencias de esta consulta**")
    for w in card["warnings"]:
        st.write(f"- `{w}` — {WARNING_TEXT.get(w, '')}")
    st.markdown("**Procedencia**")
    st.write(f"result_id `{card['result_id']}` · datos sha256 `{card['data_sha256'][:16]}…` · máscara {card['mask_version']} · "
             f"sintético: {'sí' if card['synthetic'] else 'no'}")
    for sid, url in (("S1 NASA POWER API", "https://power.larc.nasa.gov/docs/services/api/temporal/monthly/"),
                     ("S2 Fuentes meteorológicas", "https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/")):
        st.write(f"- [{sid}]({url})")


def render_downloads(bundle: Any, card: dict) -> None:
    rid = card["result_id"][:8]
    st.subheader("Ficha de detective y exportación")
    cols = st.columns(5)
    items = [("Ficha (Markdown)", bundle.evidence_md, f"ficha_{rid}.md", "text/markdown"),
             ("Ficha (JSON)", bundle.evidence_json, f"ficha_{rid}.json", "application/json"),
             ("Series (CSV)", bundle.series_csv, f"series_{rid}.csv", "text/csv"),
             ("Tendencias (CSV)", bundle.trends_csv, f"tendencias_{rid}.csv", "text/csv"),
             ("Procedencia (JSON)", bundle.provenance_json, f"procedencia_{rid}.json", "application/json")]
    for col, (label, data, name, mime) in zip(cols, items):
        col.download_button(label, data=data, file_name=name, mime=mime, width="stretch")
    st.caption("Pantalla, CSV y JSON salen del mismo resultado (result_id). Sin nombres ni datos personales.")
