"""Hefesto v2 — Detective Tico (Costa Rica). Aplicación Streamlit.

Reglas: la UI no recalcula estadística (todo viene de `src.service`); recomendación determinista
desde config/discovery.json; nunca se convierte null a 0; offline (sin teselas ni telemetría).
`HEFESTO_USE_MOCK=1` usa el mock sintético y muestra un banner permanente.
"""
from __future__ import annotations

import html
import os

import streamlit as st

from src import contracts, views
from src.contracts import QueryParams
from src.export import build_export_bundle

USE_MOCK = os.environ.get("HEFESTO_USE_MOCK") == "1"
if USE_MOCK:
    from src import service_mock as service
else:
    from src import service

SECTORS = {"CR_PN": "Pacífico Norte (entorno regional de Guanacaste)", "CR_CAR": "Caribe (entorno regional de Limón)"}
TOPICS = {"heat": "¿Ha cambiado la temperatura?", "rain": "¿Ha cambiado la lluvia anual?"}
PRESETS = {"heat": "CR_HEAT", "rain": "CR_RAIN"}


def sanitize_hypothesis(text: str | None) -> str:
    """Máx. 280 caracteres, sin HTML. No se recopilan datos personales."""
    return html.escape((text or "").strip()[:280])


def other_region(region: str) -> str:
    return "CR_CAR" if region == "CR_PN" else "CR_PN"


def init_state() -> None:
    cov = service.get_coverage()
    defaults = {"stage": "questions", "topic": "heat", "region": "CR_PN", "years": (cov["start_year"], cov["end_year"]),
                "hypothesis": "", "card": None, "bundle": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go_to(stage: str) -> None:
    st.session_state["stage"] = stage


def start_tour(topic: str) -> None:
    cov = service.get_coverage()
    st.session_state.update(topic=topic, region="CR_PN", years=(cov["start_year"], cov["end_year"]),
                            stage="confirmation", hypothesis="", card=None, bundle=None)


def banner() -> None:
    if USE_MOCK:
        st.error("⚠️ DATOS SINTÉTICOS (modo mock de desarrollo). Nada de lo que ve es un resultado científico.")
    else:
        st.caption("Datos reales NASA POWER (reanálisis, mensual 1981–2024) · explorador histórico educativo: "
                   "no pronostica sequías, inundaciones ni disponibilidad de agua.")


def sidebar() -> None:
    with st.sidebar:
        st.header("Detective Tico")
        st.caption("Recorridos guiados")
        st.button("🔥 Investiga el calor", width="stretch", on_click=start_tour, args=("heat",))
        st.button("🌧️ Investiga la lluvia", width="stretch", on_click=start_tour, args=("rain",))
        st.divider()
        st.button("↺ Nueva investigación", key="new_from_sidebar", width="stretch",
                  on_click=go_to, args=("questions",))
        st.caption("Sin cuentas, sin nombres, sin ubicación personal. Telemetría desactivada.")


def questions_step() -> None:
    cov = service.get_coverage()
    st.header("Tres preguntas para empezar")
    topics = list(TOPICS)
    topic = st.radio("1 · ¿Qué quieres investigar?", topics, index=topics.index(st.session_state["topic"]),
                     format_func=TOPICS.get, key="topic_input")
    st.session_state["topic"] = topic
    rec = contracts.recommend_variable(topic)["recommendation"]
    with st.container(border=True):
        st.markdown(f"**Variable recomendada: `{rec['variable']}`** — {rec['definition']}")
        st.write(rec["reason"])
        for item in rec["not_measured"]:
            st.caption(f"• {item}")
        st.caption("Recomendación determinista (reglas en config/discovery.json); no depende de ningún valor p.")
    sectors = list(SECTORS)
    st.session_state["region"] = st.radio(
        "2 · ¿En qué sector? (el otro se compara)", sectors, index=sectors.index(st.session_state["region"]),
        format_func=SECTORS.get, key="region_input",
    )
    st.session_state["years"] = st.slider(
        "3 · ¿Qué período?", cov["start_year"], cov["end_year"],
        value=st.session_state["years"], key="years_input",
    )
    st.button("Continuar →", type="primary", on_click=go_to, args=("confirmation",))


def confirmation_step() -> None:
    topic, region = st.session_state["topic"], st.session_state["region"]
    start, end = st.session_state["years"]
    if end < start:
        st.error("El período es inválido.")
        st.button("← Volver", on_click=go_to, args=("questions",))
        return
    rec = contracts.recommend_variable(topic)["recommendation"]
    st.header("Confirma tu investigación")
    with st.container(border=True):
        st.write(f"**Pregunta:** {TOPICS[topic]}")
        st.write(f"**Variable:** `{rec['variable']}` — {rec['definition']}")
        st.write(f"**Sector principal:** {SECTORS[region]} · **comparación:** {SECTORS[other_region(region)]}")
        st.write(f"**Período:** {start}–{end}")
        if end - start + 1 < 10:
            st.warning("Se necesitan al menos 10 años válidos para estimar una pendiente.")
        elif end - start + 1 < 30:
            st.warning("Menos de 30 años consecutivos: solo se mostrará magnitud descriptiva, sin significancia.")
    st.text_area("Hipótesis opcional (no cambia el análisis; máx. 280 caracteres)", key="hypothesis", max_chars=280,
                 placeholder="Ej.: Creo que la temperatura ha aumentado.")
    left, right = st.columns(2)
    left.button("← Cambiar", on_click=go_to, args=("questions",), width="stretch")
    if right.button("🔎 Investigar", type="primary", width="stretch"):
        query = QueryParams(rec["variable"], (region, other_region(region)), start, end, PRESETS[topic])
        try:
            card = service.build_evidence_card(query, sanitize_hypothesis(st.session_state["hypothesis"]))
        except ValueError as error:
            st.error(str(error))
            return
        if USE_MOCK:  # el mock no incluye series/procedencia en la ficha: se completan desde sus funciones
            card["series"] = [row for r in query.regions for row in service.get_annual_series(rec["variable"], r, start, end)]
            card["provenance"] = service.build_provenance(query)
            card["diagnostics"] = {}
        st.session_state["card"] = card
        st.session_state["bundle"] = build_export_bundle(card)
        st.session_state["stage"] = "results"
        st.rerun()


def results_step() -> None:
    card, bundle = st.session_state["card"], st.session_state["bundle"]
    if card is None:
        go_to("questions")
        st.rerun()
        return
    q = card["query"]
    st.header(f"Resultados · {views.VAR_NAMES[q['variable']]} · {q['start_year']}–{q['end_year']}")
    if card["hypothesis"]:
        st.write(f"**Tu hipótesis:** {card['hypothesis']}")
    st.caption(f"result_id `{card['result_id']}` · {'DATOS SINTÉTICOS' if card['synthetic'] else 'datos reales NASA POWER'}")
    views.render_cards(card)
    tabs = st.tabs(["Series anuales", "Comparar sectores", "Mapa por celda", "Mensual y estacionalidad",
                    "Episodio ENOS 1997–98", "Diagnósticos", "Límites y fuentes"])
    with tabs[0]:
        views.render_annual(card)
    with tabs[1]:
        views.render_comparison(card)
    with tabs[2]:
        views.render_map(service, card)
    with tabs[3]:
        views.render_monthly(service, card)
    with tabs[4]:
        views.render_event(service, card)
    with tabs[5]:
        views.render_diagnostics(card)
    with tabs[6]:
        topic = "heat" if q["variable"] == "T2M" else "rain"
        rule = {"not_measured": contracts.recommend_variable(topic)["recommendation"]["not_measured"]}
        views.render_limits(card, rule)
    views.render_downloads(bundle, card)
    st.button("↺ Nueva investigación", key="new_from_results", on_click=go_to, args=("questions",))


def main() -> None:
    st.set_page_config(page_title="Hefesto · Detective Tico", page_icon="🔥", layout="wide")
    init_state()
    st.title("Hefesto · Detective Tico")
    banner()
    sidebar()
    {"questions": questions_step, "confirmation": confirmation_step, "results": results_step}[
        st.session_state["stage"]]()


main()
