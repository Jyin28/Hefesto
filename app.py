import streamlit as st

st.set_page_config(
    page_title="Hefesto",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Hefesto")
st.caption("Exploración de tendencias ambientales")

st.info(
    "Entorno instalado correctamente. "
    "Todavía no se han conectado datos climáticos."
)

variable = st.selectbox(
    "Variable",
    ["Temperatura del aire a 2 m", "Precipitación"],
)

periodo = st.slider(
    "Período provisional",
    min_value=1981,
    max_value=2024,
    value=(1981, 2024),
)

st.write(f"Variable seleccionada: {variable}")
st.write(f"Período seleccionado: {periodo[0]}–{periodo[1]}")
