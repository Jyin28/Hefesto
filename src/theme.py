"""Tema visual "vidrio" de AguaAlerta (adaptado de hefesto-ui). Solo estilo: no toca datos ni estadística.
Sin fuentes ni recursos externos (offline): usa la pila de fuentes del sistema."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
:root { --ink:#0c4a6e; --sky:#0EA5E9; --mint:#10B981; }
html, body, [class*="css"], .stApp { font-family: "Plus Jakarta Sans", "Segoe UI", system-ui, sans-serif; color: var(--ink); }
code, pre, kbd { font-family: "JetBrains Mono", ui-monospace, Consolas, monospace; }
.stApp {
  background:
    radial-gradient(at 12% 18%, #38BDF8 0, transparent 50%),
    radial-gradient(at 88% 12%, #06B6D4 0, transparent 45%),
    radial-gradient(at 72% 92%, #34D399 0, transparent 50%),
    radial-gradient(at 8% 88%, #10B981 0, transparent 38%),
    linear-gradient(135deg, #F0F9FF, #BAE6FD);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: var(--ink); font-weight: 800; letter-spacing: -.01em; }
.block-container > div > [data-testid="stVerticalBlock"] { gap: 1rem; }
[data-testid="stSidebar"] {
  background: rgba(255,255,255,.65); backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid rgba(255,255,255,.7);
}
[data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stAlert"],
[data-testid="stForm"], [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
  background: rgba(255,255,255,.58); border: 1px solid rgba(255,255,255,.75); border-radius: 1rem;
  box-shadow: 0 10px 24px -14px rgba(14,165,233,.35), inset 0 1px 1px rgba(255,255,255,.9);
}
[data-testid="stMetric"], [data-testid="stAlert"] { padding: .75rem 1rem; }
[data-testid="stPlotlyChart"] { padding: .5rem; }
[data-testid="stExpander"] details { border: 0; }
.stButton > button, .stDownloadButton > button {
  border-radius: 999px; font-weight: 700; padding: .5rem 1.2rem; color: #0369a1;
  background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(186,230,253,.55));
  border: 1px solid rgba(255,255,255,.9);
  box-shadow: 0 6px 14px -6px rgba(14,165,233,.45), inset 0 1px 1px rgba(255,255,255,.95);
  transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .2s;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px) scale(1.03); color: #0369a1; border-color: #fff; }
.stButton > button:active { transform: scale(.97); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  color: #fff; background: linear-gradient(180deg, #34D399, #0EA5E9);
  box-shadow: 0 8px 18px -6px rgba(16,185,129,.6), inset 0 1px 1px rgba(255,255,255,.7);
}
.stButton > button[kind="primary"]:hover { color: #fff; }
button:focus-visible, [role="tab"]:focus-visible, input:focus-visible { outline: 3px solid var(--mint) !important; outline-offset: 2px; }
[data-baseweb="tab-list"] { gap: .4rem; }
[data-baseweb="tab"] { border-radius: 999px; padding: .35rem 1rem; background: rgba(255,255,255,.55); font-weight: 700; }
[data-baseweb="tab"][aria-selected="true"] { color: #fff; background: linear-gradient(180deg, #34D399, #0EA5E9); }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }
[data-testid="stRadio"] label, [data-testid="stSelectbox"] label, [data-testid="stSlider"] label { font-weight: 700; color: #0369a1; }
@media (prefers-reduced-motion: reduce) { .stButton > button { transition: none; } }
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
