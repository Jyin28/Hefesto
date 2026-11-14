"""Hefesto v2 — Aplicación Principal: Detective Tico.

Fase 1: Configuración Offline y Esqueleto Streamlit.
Propietario de UI: Kevin.

Reglas normativas:
1. Cero recálculo estadístico en la UI: todos los cálculos provienen exclusivamente
   del servicio (service_mock en F1 / service en producción).
2. Flujo de 3 preguntas guiadas con pantalla de confirmación previa obligatoria.
3. Recomendación determinista de variable (T2M para calor, PRECTOTCORR para lluvia)
   sin cajas negras ni ranking por valor p.
4. Banner permanente de datos sintéticos cuando synthetic=True.
5. Cero conversión de null a 0 o False: valores ausentes se muestran como 'N/D' o 'No evaluable'.
6. Sanitización de hipótesis (máx 280 caracteres, sin HTML, sin datos personales).
7. Contenedores modulares listos para conectar src/views.py y src/export.py en Fase 2.
"""
from __future__ import annotations

import html
import os
from typing import Any

import streamlit as st

from src import contracts

# El asistente de preguntas se conserva como demostración sintética explícita.
from src import service_mock as service

# Imports limpios hacia módulos de visualización y exportación (Fase 2)
try:
    from src import views  # type: ignore
except ImportError:
    views = None

try:
    from src import export  # type: ignore
except ImportError:
    export = None


# ==============================================================================
# Contratos normativos y recomendaciones deterministas
# ==============================================================================

def recommend_variable(topic: str) -> dict[str, Any]:
    """Recomendación determinista y transparente según el tema de investigación.

    Cumple con el contrato normativo: sin ranking por p-valor ni selecciones opacas.
    topic: 'heat' | 'rain' -> dict con variable, preset_id, label, reason, definition, limitations, etc.
    """
    if topic == "heat":
        return {
            "topic": "heat",
            "variable": "T2M",
            "preset_id": "CR_HEAT",
            "title": "Calor ambiental",
            "label": "Temperatura media del aire a 2 m (T2M)",
            "reason": (
                "Para estudiar variaciones térmicas a escala climática, "
                "la magnitud física estándar es la temperatura media del aire medida a 2 metros "
                "de la superficie."
            ),
            "definition": (
                "Estimación de la temperatura media anual del aire a 2 metros sobre el suelo "
                "procedente de modelos de reanálisis atmosférico con asimilación de datos globales."
            ),
            "limitations": (
                "Datos de reanálisis en celdas de ~50 km × 60 km (decenas de kilómetros). "
                "Representan el promedio de una región amplia, no la medición puntual del termómetro "
                "de tu escuela o patio. No son un pronóstico del tiempo meteorológico diario."
            ),
            "unit_annual": contracts.ANNUAL_UNITS.get("T2M", "degC"),
            "unit_slope": contracts.SLOPE_UNITS.get("T2M", "degC/decade"),
        }
    elif topic == "rain":
        return {
            "topic": "rain",
            "variable": "PRECTOTCORR",
            "preset_id": "CR_RAIN",
            "title": "Lluvia y precipitación",
            "label": "Precipitación corregida acumulada anual (PRECTOTCORR)",
            "reason": (
                "Para evaluar si llueve más o menos a lo largo de las décadas, se utiliza "
                "la precipitación acumulada corregida anual, que suma el agua caída en cada mes del año."
            ),
            "definition": (
                "Tasa de precipitación corregida por asimilación; el valor anual representa "
                "los milímetros totales de lluvia acumulados por año (mm/año)."
            ),
            "limitations": (
                "Resolución espacial regional de decenas de kilómetros. No mide directamente "
                "el caudal de un río local, la recarga de mantos acuíferos subterráneos ni la humedad "
                "en la raíz del suelo. No reemplaza los pluviómetros de una finca o estación local."
            ),
            "unit_annual": contracts.ANNUAL_UNITS.get("PRECTOTCORR", "mm/yr"),
            "unit_slope": contracts.SLOPE_UNITS.get("PRECTOTCORR", "mm/yr/decade"),
        }
    else:
        raise ValueError(f"Tema no reconocido: {topic!r}. Opciones válidas: 'heat', 'rain'.")


def sanitize_hypothesis(text: str | None) -> str:
    """Sanitiza y trunca la hipótesis opcional del estudiante a 280 caracteres.

    Garantiza que no haya inyección de HTML ni etiquetas maliciosas. Cero datos personales.
    """
    if not text:
        return ""
    clean = html.escape(text.strip()[:280])
    return clean[:280]


def format_p_value(p: float | None) -> str:
    """Formatea valores p sin redondear destructivamente a 0.000 ni convertir null a 0."""
    if p is None:
        return "N/D (null)"
    if p < 0.001:
        return "< 0.001"
    return f"{p:.4f}"


def format_number(val: float | None, decimals: int = 2, unit: str = "") -> str:
    """Formatea números flotantes preservando None como N/D."""
    if val is None:
        return "N/D"
    unit_str = f" {unit}" if unit else ""
    return f"{val:.{decimals}f}{unit_str}"


def format_significance_badge(significant: bool | None, level: str, status: str) -> tuple[str, str]:
    """Retorna etiqueta didáctica y explicación rigurosa.

    Diferencia estrictamente 'No evaluable' (None) de 'No significativo' (False).
    """
    if status == "insufficient_data" or level == "none":
        return (
            "⚪ No evaluable",
            "Registro insuficiente (menos de 10 años). No es estadísticamente viable ajustar una tendencia."
        )
    if level == "descriptive":
        return (
            "🟡 Solo descriptivo (No evaluable)",
            "Registro intermedio (10 a 29 años). Permite observar la pendiente histórica, pero no tiene soporte para inferencia multidecadal."
        )
    if significant is True:
        return (
            "🟢 Cambio estadísticamente significativo",
            "La evidencia estadística descarta el azar (q < 0.05 tras corrección por pruebas múltiples FDR BY)."
        )
    elif significant is False:
        return (
            "🟠 No significativo estadísticamente",
            "Evidencia estadística insuficiente para descartar el azar. ¡Importante: No significa ausencia de cambio ni prueba de que no cambie!"
        )
    return ("⚪ No evaluable", "Datos no evaluables para inferencia estadística.")


def generate_result_id(preset_id: str, variable: str, primary: str, comp: str, start: int, end: int) -> str:
    """Genera un identificador de resultado determinista compartido entre UI y exportaciones."""
    return f"hefesto_v2_{preset_id}_{primary}_{comp}_{start}_{end}"


# Mapeo descriptivo de regiones para el estudiante
REGION_LABELS = {
    "CR_PN": "Pacífico Norte (CR_PN)",
    "CR_CAR": "Caribe (CR_CAR)",
}

REGION_DESCRIPTIONS = {
    "CR_PN": "Sector Pacífico Norte (entorno regional de Guanacaste, vertiente Pacífica)",
    "CR_CAR": "Sector Caribe (entorno regional de Limón, vertiente Atlántica/Caribe)",
}

def get_counterpart_region(region_id: str) -> str:
    """Devuelve la región de contraste automático para comparaciones objetivas."""
    return "CR_CAR" if region_id == "CR_PN" else "CR_PN"


# ==============================================================================
# Manejo del estado de sesión (st.session_state)
# ==============================================================================

def init_session_state(coverage: dict[str, Any]) -> None:
    """Inicializa el estado de sesión si no existe."""
    min_year = coverage.get("start_year", contracts.COVERAGE_START_YEAR)
    max_year = coverage.get("end_year", contracts.COVERAGE_END_YEAR)

    if "stage" not in st.session_state:
        st.session_state["stage"] = "questions"  # 'questions' | 'confirmation' | 'results'
    if "topic" not in st.session_state:
        st.session_state["topic"] = "heat"       # 'heat' | 'rain'
    if "primary_region" not in st.session_state:
        st.session_state["primary_region"] = "CR_PN"
    if "start_year" not in st.session_state:
        st.session_state["start_year"] = min_year
    if "end_year" not in st.session_state:
        st.session_state["end_year"] = max_year
    if "raw_hypothesis" not in st.session_state:
        st.session_state["raw_hypothesis"] = ""
    if "sanitized_hypothesis" not in st.session_state:
        st.session_state["sanitized_hypothesis"] = ""
    if "investigation_bundle" not in st.session_state:
        st.session_state["investigation_bundle"] = None
    if "result_id" not in st.session_state:
        st.session_state["result_id"] = ""


# ==============================================================================
# Componentes visuales de la aplicación
# ==============================================================================

def render_synthetic_banner(is_synthetic: bool) -> None:
    """Muestra el banner superior permanente e inequívoco si los datos son sintéticos."""
    if is_synthetic:
        st.warning(
            "⚠️ **AVISO METODOLÓGICO: DATOS SINTÉTICOS DE PRUEBA (MOCK)** — "
            "Esta instancia está utilizando el servicio de simulación (`service_mock`). "
            "Los valores numéricos son ejemplos deterministas de prueba para verificación de contratos y desarrollo, "
            "**NO constituyen evidencia científica real de la NASA ni observaciones validadas**.",
            icon="⚠️",
        )


def render_sidebar(coverage: dict[str, Any]) -> None:
    """Barra lateral con accesos rápidos y contexto didáctico."""
    with st.sidebar:
        st.title("🕵️‍♂️ Detective Tico")
        st.caption("Plataforma educativa para investigar tendencias climáticas en Costa Rica.")

        st.markdown("---")
        st.subheader("⚡ Atajos rápidos (Presets)")
        st.write("Carga directamente uno de los dos recorridos guiados oficiales:")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔥 Calor\n(`CR_HEAT`)", use_container_width=True):
                st.session_state["topic"] = "heat"
                st.session_state["primary_region"] = "CR_PN"
                st.session_state["start_year"] = coverage.get("start_year", 1981)
                st.session_state["end_year"] = coverage.get("end_year", 2024)
                st.session_state["stage"] = "confirmation"
                st.rerun()

        with col_b:
            if st.button("🌧️ Lluvia\n(`CR_RAIN`)", use_container_width=True):
                st.session_state["topic"] = "rain"
                st.session_state["primary_region"] = "CR_PN"
                st.session_state["start_year"] = coverage.get("start_year", 1981)
                st.session_state["end_year"] = coverage.get("end_year", 2024)
                st.session_state["stage"] = "confirmation"
                st.rerun()

        st.markdown("---")
        st.subheader("📖 Guía de investigación")
        st.markdown(
            "1. **Pregunta:** Elige qué fenómeno ambiental te interesa.\n"
            "2. **Sector:** Escoge el sector principal; el otro se compara automáticamente.\n"
            "3. **Período:** Selecciona la ventana temporal.\n"
            "4. **Confirmación:** Revisa la recomendación física y sus límites antes de consultar."
        )

        st.markdown("---")
        st.caption("Hefesto v2 · Costa Rica · Cobertura 1981–2024")


def render_questions_step(coverage: dict[str, Any]) -> None:
    """Paso interactivo con las 3 preguntas guiadas."""
    st.header("🔍 Formulación de la Investigación")
    st.write(
        "Bienvenido a **Detective Tico**. Responde las 3 preguntas para construir tu consulta científica "
        "sin sesgos y con total transparencia metodológica."
    )

    min_cov = coverage.get("start_year", contracts.COVERAGE_START_YEAR)
    max_cov = coverage.get("end_year", contracts.COVERAGE_END_YEAR)

    # --------------------------------------------------------------------------
    # Paso 1: Pregunta sobre el fenómeno
    # --------------------------------------------------------------------------
    st.markdown("### Paso 1: ¿Qué quieres investigar?")
    topic_options = {
        "heat": "🔥 Calor ambiental (Temperatura media del aire a 2 m)",
        "rain": "🌧️ Lluvia y precipitación (Precipitación acumulada anual corregida)",
    }
    selected_topic = st.radio(
        "Selecciona el fenómeno físico:",
        options=list(topic_options.keys()),
        format_func=lambda k: topic_options[k],
        index=0 if st.session_state["topic"] == "heat" else 1,
        help="Hefesto asignará deterministamente la variable física idónea sin alterar el análisis.",
    )

    # --------------------------------------------------------------------------
    # Paso 2: Sector de estudio con comparación automática
    # --------------------------------------------------------------------------
    st.markdown("### Paso 2: ¿En qué sector de Costa Rica quieres enfocarte?")
    sector_options = {
        "CR_PN": "🌊 Pacífico Norte (CR_PN) — Guanacaste y vertiente Pacífica",
        "CR_CAR": "🌴 Caribe (CR_CAR) — Limón y vertiente Atlántica/Caribe",
    }
    selected_primary = st.radio(
        "Selecciona el sector prioritario:",
        options=list(sector_options.keys()),
        format_func=lambda k: sector_options[k],
        index=0 if st.session_state["primary_region"] == "CR_PN" else 1,
        help="El otro sector se analizará automáticamente como contraparte de comparación.",
    )

    counterpart = get_counterpart_region(selected_primary)
    st.info(
        f"💡 **Comparación automática garantizada:** Al seleccionar **{REGION_LABELS[selected_primary]}**, "
        f"el sistema incluirá automáticamente a **{REGION_LABELS[counterpart]}** como sector de contraste. "
        "En ciencia climática las comparaciones regionales evitan conclusiones apresuradas.",
        icon="ℹ️",
    )

    # --------------------------------------------------------------------------
    # Paso 3: Selector de período
    # --------------------------------------------------------------------------
    st.markdown("### Paso 3: ¿Qué período de años deseas abarcar?")
    current_start = max(min_cov, min(st.session_state["start_year"], max_cov))
    current_end = min(max_cov, max(st.session_state["end_year"], min_cov))
    if current_start > current_end:
        current_start, current_end = min_cov, max_cov

    year_range = st.slider(
        "Rango de años a investigar (cobertura disponible):",
        min_value=min_cov,
        max_value=max_cov,
        value=(current_start, current_end),
        step=1,
        help="El período por defecto es 1981–2024 (44 años completos).",
    )
    start_y, end_y = year_range
    n_years = end_y - start_y + 1

    # Indicador didáctico de longitud del registro
    if n_years >= 30:
        st.success(
            f"✅ **Registro multidecadal robusto:** {n_years} años seleccionados ({start_y}–{end_y}). "
            "Cumple con el criterio estándar (≥ 30 años) para análisis de tendencias con inferencia estadística.",
            icon="✅",
        )
    elif 10 <= n_years < 30:
        st.warning(
            f"⚠️ **Registro intermedio:** {n_years} años seleccionados ({start_y}–{end_y}). "
            "Entre 10 y 29 años solo se permite análisis descriptivo. No es metodológicamente apto para inferencia multidecadal.",
            icon="⚠️",
        )
    else:
        st.error(
            f"🛑 **Registro insuficiente:** {n_years} años seleccionados ({start_y}–{end_y}). "
            "Menos de 10 años no permite ajustar tendencias estadísticas (resultado: 'No evaluable').",
            icon="🛑",
        )

    st.markdown("---")
    # Botón para continuar a la confirmación previa
    if st.button("Continuar a la Pantalla de Confirmación Previa ➡️", type="primary"):
        st.session_state["topic"] = selected_topic
        st.session_state["primary_region"] = selected_primary
        st.session_state["start_year"] = start_y
        st.session_state["end_year"] = end_y
        st.session_state["stage"] = "confirmation"
        st.rerun()


def render_confirmation_step() -> None:
    """Pantalla de confirmación previa obligatoria antes de ejecutar la consulta."""
    st.header("📋 Pantalla de Confirmación Previa")
    st.write(
        "Antes de consultar los datos y ejecutar el análisis, revisa la recomendación científica "
        "determinista, la definición formal de la variable y los límites metodológicos de los datos:"
    )

    topic = st.session_state["topic"]
    primary_reg = st.session_state["primary_region"]
    comp_reg = get_counterpart_region(primary_reg)
    start_y = st.session_state["start_year"]
    end_y = st.session_state["end_year"]
    n_years = end_y - start_y + 1

    rec = recommend_variable(topic)

    # Tarjeta de recomendación determinista
    st.subheader(f"1. Recomendación Científica: {rec['title']}")
    with st.container(border=True):
        st.markdown(f"**Variable asignada:** `{rec['variable']}` — **{rec['label']}**")
        st.markdown(f"**¿Por qué esta variable?** {rec['reason']}")
        st.markdown(f"**Definición en lenguaje sencillo:** {rec['definition']}")
        st.markdown(f"**Unidad de análisis anual:** `{rec['unit_annual']}` | **Unidad de cambio:** `{rec['unit_slope']}`")

        st.warning(
            f"⚠️ **Límites metodológicos de los datos:**\n\n{rec['limitations']}",
            icon="⚠️",
        )

    # Tarjeta de diseño del estudio
    st.subheader("2. Diseño de la Comparación Regional")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sector prioritario", REGION_LABELS[primary_reg])
            st.caption(REGION_DESCRIPTIONS[primary_reg])
        with col2:
            st.metric("Sector de comparación", REGION_LABELS[comp_reg])
            st.caption(REGION_DESCRIPTIONS[comp_reg])
        with col3:
            st.metric("Período de estudio", f"{start_y}–{end_y}")
            st.caption(f"{n_years} años consecutivos")

    # Registro de hipótesis opcional (sanitizada y segura)
    st.subheader("3. Hipótesis del Detective (Opcional)")
    hypothesis_input = st.text_input(
        "Formula lo que esperas encontrar antes de ver los resultados (máx. 280 caracteres):",
        value=st.session_state.get("raw_hypothesis", ""),
        placeholder="Ej: Sospecho que en Guanacaste el calor ha aumentado a un ritmo mayor que en Limón...",
        max_chars=280,
        help="Tus palabras se registrarán en la ficha de evidencia. No ingreses nombres ni datos personales.",
    )

    st.markdown("---")
    # Botones de acción: volver atrás vs confirmar
    col_back, col_confirm = st.columns([1, 1])

    with col_back:
        if st.button("⬅ Volver atrás a cambiar respuestas", use_container_width=True):
            # Regresa al paso de preguntas sin alterar ni ejecutar ningún análisis
            st.session_state["raw_hypothesis"] = hypothesis_input
            st.session_state["stage"] = "questions"
            st.rerun()

    with col_confirm:
        if st.button("🔍 Confirmar e Iniciar Investigación", type="primary", use_container_width=True):
            # Sanitizar hipótesis (TK-06)
            clean_hyp = sanitize_hypothesis(hypothesis_input)
            st.session_state["raw_hypothesis"] = hypothesis_input
            st.session_state["sanitized_hypothesis"] = clean_hyp

            # Construir QueryParams
            query = contracts.QueryParams(
                variable=rec["variable"],
                regions=(primary_reg, comp_reg),
                start_year=start_y,
                end_year=end_y,
                preset_id=rec["preset_id"],
            )

            # Ejecutar consumo exclusivo del servicio (cero recálculo en UI)
            comparison_data = service.get_comparison(
                variable=query.variable,
                start_year=query.start_year,
                end_year=query.end_year,
                regions=query.regions,
            )

            # Obtener series anuales para ambos sectores
            series_primary = service.get_annual_series(
                variable=query.variable,
                region_id=primary_reg,
                start_year=query.start_year,
                end_year=query.end_year,
            )
            series_comp = service.get_annual_series(
                variable=query.variable,
                region_id=comp_reg,
                start_year=query.start_year,
                end_year=query.end_year,
            )

            result_id = generate_result_id(
                preset_id=query.preset_id,
                variable=query.variable,
                primary=primary_reg,
                comp=comp_reg,
                start=start_y,
                end=end_y,
            )

            # Guardar paquete de resultados en session_state
            st.session_state["result_id"] = result_id
            st.session_state["investigation_bundle"] = {
                "query": query,
                "recommendation": rec,
                "comparison": comparison_data,
                "series": {
                    primary_reg: series_primary,
                    comp_reg: series_comp,
                },
                "result_id": result_id,
                "hypothesis": clean_hyp,
                "synthetic": comparison_data.get("synthetic", True),
            }

            st.session_state["stage"] = "results"
            st.rerun()


def render_results_step() -> None:
    """Pantalla con los resultados de la investigación y contenedores listos para Fase 2."""
    bundle = st.session_state.get("investigation_bundle")
    if not bundle:
        st.session_state["stage"] = "questions"
        st.rerun()
        return

    query: contracts.QueryParams = bundle["query"]
    rec: dict[str, Any] = bundle["recommendation"]
    comparison: dict[str, Any] = bundle["comparison"]
    result_id: str = bundle["result_id"]
    hypothesis: str = bundle.get("hypothesis", "")
    primary_reg = query.regions[0]
    comp_reg = query.regions[1]

    # Barra superior de navegación y metadatos
    col_title, col_action = st.columns([3, 1])
    with col_title:
        st.header(f"🎯 Resultados: {rec['title']} ({query.preset_id})")
        st.caption(f"Identificador de resultado único (`result_id`): `{result_id}`")
    with col_action:
        if st.button("🔄 Nueva investigación", use_container_width=True):
            st.session_state["investigation_bundle"] = None
            st.session_state["stage"] = "questions"
            st.rerun()

    if hypothesis:
        st.info(f"💡 **Hipótesis del detective:** *«{hypothesis}»*", icon="💡")

    # Extraer resultados de cada región desde la comparación
    results_list = comparison.get("results", [])
    res_primary = next((r for r in results_list if r["region_id"] == primary_reg), None)
    res_comp = next((r for r in results_list if r["region_id"] == comp_reg), None)

    # --------------------------------------------------------------------------
    # Las 4 Tarjetas de Respuesta del Detective Tico (Qué, Dónde, Cuánto, Evidencia)
    # --------------------------------------------------------------------------
    st.markdown("### 📋 Ficha de Evidencia — Las 4 Respuestas")

    tab_pri, tab_comp = st.tabs([
        f"Sector Principal: {REGION_LABELS[primary_reg]}",
        f"Sector Comparación: {REGION_LABELS[comp_reg]}",
    ])

    for tab, target_reg, r_data in [
        (tab_pri, primary_reg, res_primary),
        (tab_comp, comp_reg, res_comp),
    ]:
        with tab:
            if r_data is None:
                st.error("No se encontraron resultados para esta región en la respuesta del servicio.")
                continue

            card1, card2, card3, card4 = st.columns(4)

            # Tarjeta 1: Qué
            with card1:
                with st.container(border=True):
                    st.markdown("**1. ¿Qué?**")
                    st.caption("Variable y definición física")
                    st.write(f"**{rec['variable']}**")
                    st.caption(rec["label"])
                    st.write(f"Unidad anual: `{r_data.get('slope_unit', '').replace('/decade', '')}`")

            # Tarjeta 2: Dónde
            with card2:
                with st.container(border=True):
                    st.markdown("**2. ¿Dónde?**")
                    st.caption("Sector y cobertura")
                    st.write(f"**{REGION_LABELS[target_reg]}**")
                    cov_frac = r_data.get("coverage_fraction")
                    st.caption(f"Cobertura espacial: {format_number(cov_frac * 100 if cov_frac is not None else None, 1)} %")
                    st.caption("Celdas regionales ~50 km")

            # Tarjeta 3: Cuánto
            with card3:
                with st.container(border=True):
                    st.markdown("**3. ¿Cuánto?**")
                    st.caption("Cambio y pendiente")
                    slope = r_data.get("slope_per_decade")
                    slope_unit = r_data.get("slope_unit", "")
                    st.metric(
                        "Pendiente por década",
                        format_number(slope, 3, slope_unit),
                    )
                    tot_change = r_data.get("total_change")
                    st.caption(f"Cambio total: {format_number(tot_change, 2)}")
                    ci_l = r_data.get("ci_low")
                    ci_h = r_data.get("ci_high")
                    if ci_l is not None and ci_h is not None:
                        st.caption(f"IC 95 %: [{ci_l:.3f}, {ci_h:.3f}]")
                    else:
                        st.caption("IC 95 %: N/D")

            # Tarjeta 4: Evidencia
            with card4:
                with st.container(border=True):
                    st.markdown("**4. Evidencia**")
                    st.caption("Rigor e inferencia")
                    level = r_data.get("level", "none")
                    status = r_data.get("status", "ok")
                    significant = r_data.get("significant")
                    badge_title, badge_desc = format_significance_badge(significant, level, status)
                    st.write(f"**{badge_title}**")
                    st.caption(badge_desc)

                    p_raw = r_data.get("p_value")
                    p_adj = r_data.get("p_adjusted")
                    st.caption(f"p original: `{format_p_value(p_raw)}` | q (FDR BY): `{format_p_value(p_adj)}`")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # Contenedor 1: Visualizaciones Científicas (src/views.py)
    # --------------------------------------------------------------------------
    views_container = st.container()
    with views_container:
        st.subheader("📊 Visualizaciones Científicas")
        if views is not None and hasattr(views, "render_investigation_views"):
            # Enlace con Fase 2 cuando views.py esté implementado
            views.render_investigation_views(bundle)
        else:
            st.info(
                "🧩 **Contenedor listo para `src/views.py` (Fase 2):** "
                "Aquí se conectarán los gráficos Plotly de serie anual con banda de confianza "
                "y el mapa de celdas regional sin teselas externas.",
                icon="📊",
            )
            # Resumen visual previo con componentes nativos mientras se implementa Fase 2
            with st.expander("Ver serie anual de datos suministrada por el servicio (tabla sin recálculo):"):
                col_tab1, col_tab2 = st.columns(2)
                with col_tab1:
                    st.caption(f"Serie anual {REGION_LABELS[primary_reg]}")
                    st.dataframe(bundle["series"][primary_reg], use_container_width=True)
                with col_tab2:
                    st.caption(f"Serie anual {REGION_LABELS[comp_reg]}")
                    st.dataframe(bundle["series"][comp_reg], use_container_width=True)

    st.markdown("---")

    # --------------------------------------------------------------------------
    # Contenedor 2: Exportación de Evidencia (src/export.py)
    # --------------------------------------------------------------------------
    export_container = st.container()
    with export_container:
        st.subheader("📦 Ficha y Exportación de Evidencia")
        if export is not None and hasattr(export, "render_export_section"):
            # Enlace con Fase 2 cuando export.py esté implementado
            export.render_export_section(bundle)
        else:
            st.info(
                "🧩 **Contenedor listo para `src/export.py` (Fase 2):** "
                "Aquí se conectará la descarga de la Ficha de Detective (`evidence.json`, "
                "`evidence.md`) y las series tabulares (`series.csv`, `trends.csv`) con `result_id` compartido.",
                icon="📦",
            )

    # --------------------------------------------------------------------------
    # Pie de página y metadatos de procedencia
    # --------------------------------------------------------------------------
    st.markdown("---")
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.caption(f"**Esquema:** Hefesto v{contracts.SCHEMA_VERSION}")
    with meta_cols[1]:
        st.caption(f"**Familia de pruebas:** `{comparison.get('family_metadata', [{}])[0].get('family_id', 'N/D')}`")
    with meta_cols[2]:
        st.caption(f"**Método:** {res_primary.get('method', 'N/D') if res_primary else 'N/D'}")
    with meta_cols[3]:
        st.caption(f"**result_id:** `{result_id}`")


# ==============================================================================
# Función principal
# ==============================================================================

def main() -> None:
    """Punto de entrada de la aplicación Streamlit."""
    st.set_page_config(
        page_title="Hefesto — Detective Tico",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Cobertura y metadatos del servicio
    coverage = service.get_coverage()
    is_synthetic = coverage.get("synthetic", True)

    # Inicializar estado de sesión
    init_session_state(coverage)

    # Banner superior permanente para datos sintéticos (Regla 5)
    render_synthetic_banner(is_synthetic)

    # Barra lateral
    render_sidebar(coverage)

    # Título principal
    st.title("🌍 Hefesto — Detective Tico")
    st.caption("Investigación de tendencias climáticas y ambientales en Costa Rica con datos satelitales.")

    # Control de flujo de estados (Wizard 3 preguntas -> Confirmación -> Resultados)
    current_stage = st.session_state.get("stage", "questions")

    if current_stage == "questions":
        render_questions_step(coverage)
    elif current_stage == "confirmation":
        render_confirmation_step()
    elif current_stage == "results":
        render_results_step()
    else:
        st.session_state["stage"] = "questions"
        st.rerun()


if __name__ == "__main__":
    if os.getenv("HEFESTO_USE_MOCK") == "1":
        main()
    else:
        from src.dashboard import main as run_dashboard

        run_dashboard()
