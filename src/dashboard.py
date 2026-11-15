"""Streamlit implementation of the AguaAlerta MVP."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .contracts import ANNUAL_UNITS, COVERAGE_END_YEAR, COVERAGE_START_YEAR, to_json
from .export import csv_tables, evidence_card, format_csv
from .regions import REGION_SPECS
from .statistics import default_windows


def display_number(value):
    return "Sin dato" if value is None else f"{value:.3g}"


def display_unit(unit):
    return {"degC": "°C", "mm/yr": "mm/año", "mm/month": "mm/mes",
            "degC/decade": "°C/década", "mm/yr/decade": "mm/año por década"}.get(unit, unit)


def cell_map(cells, key, color_range, title, unit):
    features = []
    for cell in cells:
        west, south, east, north = cell["bbox"]
        features.append({
            "type": "Feature", "id": cell["id"], "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [
                [[west, south], [east, south], [east, north], [west, north], [west, south]],
            ]},
        })
    values = [cell.get(key) for cell in cells]
    low, high = color_range
    figure = go.Figure()
    geojson = {"type": "FeatureCollection", "features": features}
    for available in (False, True):
        positions = [i for i, value in enumerate(values) if (value is not None) == available]
        if not positions:
            continue
        figure.add_trace(go.Choropleth(
            geojson=geojson, locations=[cells[i]["id"] for i in positions],
            z=[values[i] if available else 0 for i in positions],
            zmin=low if available else 0, zmax=high if available else 1,
            colorscale="RdBu_r" if available else [[0, "#cbd5e1"], [1, "#cbd5e1"]],
            showscale=available, colorbar={"title": unit},
            marker_line_width=[3 if key == "long_term_slope" and cells[i]["significant"] else 1 for i in positions],
            hovertemplate=("%{location}<br>%{z:.2f} " + unit if available else "%{location}<br>Sin dato")
            + "<extra></extra>",
        ))
    figure.add_trace(go.Scattergeo(
        lon=[cell["lon"] for cell in cells], lat=[cell["lat"] for cell in cells],
        customdata=[cell["id"] for cell in cells], mode="markers", showlegend=False,
        marker={"size": 12, "color": "#233c42", "line": {"width": 1, "color": "white"}},
        hovertemplate="%{customdata}<extra></extra>",
    ))
    figure.update_geos(fitbounds="locations", visible=False)
    figure.update_layout(title=title, height=300, margin=dict(l=0, r=0, t=45, b=0))
    return st.plotly_chart(figure, width="stretch", on_select="rerun",
                           selection_mode="points", key=f"map-{key}").selection


def display_card(card):
    comparison = card["comparison"]
    trend = card["trend"]
    unit = display_unit(comparison["window_a"]["unit"])
    slope_unit = display_unit(trend["slope_unit"])
    selected = pd.DataFrame(card["series"]).set_index("year")
    st.line_chart(selected["value"], y_label=unit)
    columns = st.columns(3)
    for index, name in enumerate(("window_a", "window_b")):
        window = comparison[name]
        columns[index].metric(f"{window['start_year']}–{window['end_year']} ({window['n_years']} años)",
                              f"{display_number(window['mean'])} {unit}" if window["mean"] is not None else "Sin dato")
        if window["slope_per_decade"] is not None:
            columns[index].caption(f"Pendiente {display_number(window['slope_per_decade'])} {slope_unit}")
    columns[2].metric("Cambio de promedio (B − A)", display_number(comparison["mean_diff_b_minus_a"]))
    columns[2].caption(f"Cambio de pendiente {display_number(comparison['slope_diff_b_minus_a'])} {slope_unit}")
    st.subheader("Evidencia de largo plazo")
    st.write(f"**{display_number(trend['slope_per_decade'])} {slope_unit}** "
             f" · {trend['n_years']} años completos · {trend['method']}")
    if trend["p_value"] is not None:
        st.write(f"IC individual del 95 %: {display_number(trend['ci_low'])} a {display_number(trend['ci_high'])}. "
                 f"p ajustado BY: {display_number(trend['p_adjusted'])}. "
                 + ("Evidencia al 5 %." if trend["significant"] else "Evidencia insuficiente al 5 %."))
    with st.expander("Sensibilidad HAC y comprobación Sen/Mann–Kendall"):
        mk = card["evidence"]["mann_kendall"]
        st.write(f"Sen: {display_number(mk['slope_per_decade'])} {slope_unit}. "
                 f"p de Mann–Kendall ajustado BY: {display_number(mk['p_adjusted'])}.")
        if card["methods_disagree"]:
            st.write("OLS/HAC y Mann–Kendall difieren en su conclusión al 5 %.")
        st.dataframe(card["evidence"]["hac_sensitivity"])
        st.json(card["families"], expanded=False)


def main():
    st.set_page_config(page_title="AguaAlerta", layout="wide")
    st.title("AguaAlerta")
    st.caption("Compara el calor y la lluvia en dos sectores de Costa Rica con datos de NASA POWER.")
    st.markdown(
        "<style>@media print { [data-testid='stHeader'], [data-testid='stToolbar'], "
        "[data-testid='stDownloadButton'] { display: none !important; } "
        "[data-testid='stMainBlockContainer'] { padding: 0 !important; } }</style>",
        unsafe_allow_html=True,
    )
    columns = st.columns(2)
    variable = columns[0].radio("Recorrido", ("T2M", "PRECTOTCORR"), horizontal=True,
                                format_func={"T2M": "Temperatura", "PRECTOTCORR": "Lluvia"}.get)
    region = columns[1].selectbox("Sector climático", tuple(REGION_SPECS),
                                  format_func=lambda key: REGION_SPECS[key].name)
    first, last = COVERAGE_START_YEAR, COVERAGE_END_YEAR
    default_a, default_b = default_windows(first, last)
    with st.expander("Ajustar ventanas"):
        window_a = st.slider("Ventana A", first, last, default_a)
        window_b = st.slider("Ventana B", first, last, default_b)

    try:
        regional = evidence_card(region, variable, window_a=window_a, window_b=window_b)
    except (ValueError, OSError) as error:
        st.error(f"No se pudo abrir el paquete climático: {error}")
        return

    st.subheader("Comparación por celda")
    cells = regional["cells"]
    values = [cell[key] for cell in cells for key in ("window_a_mean", "window_b_mean")
              if cell.get(key) is not None]
    scale = (min(values), max(values)) if values else (0, 1)
    if scale[0] == scale[1]:
        scale = (scale[0] - 0.5, scale[1] + 0.5)
    unit = display_unit(ANNUAL_UNITS[variable])
    maps = st.columns(2)
    for column, window, key in zip(maps, (window_a, window_b), ("window_a_mean", "window_b_mean")):
        with column:
            label = f"{window[0]}–{window[1]}"
            state = cell_map(cells, key, scale, label, unit)
            signature = (state.points, variable, region, window)
            state_key = f"last_selection_{key}"
            if state.points and st.session_state.get(state_key) != signature:
                location = state.points[0].get("customdata") or state.points[0].get("location")
                if any(cell["id"] == location for cell in cells):
                    st.session_state[f"cell_{region}"] = location
            st.session_state[state_key] = signature
    st.caption(f"Escala compartida de {display_number(scale[0])} a {display_number(scale[1])} {unit}. "
               "Las celdas grises carecen de dato.")
    with st.expander("Mapa de evidencia de largo plazo"):
        extent = max((abs(cell["long_term_slope"]) for cell in cells
                      if cell["long_term_slope"] is not None), default=0) or 1
        cell_map(cells, "long_term_slope", (-extent, extent), "Pendiente por celda", f"{unit}/década")
        st.caption("Contorno grueso: evidencia al 5 % con ajuste BY para ambas zonas.")
    cell_id = st.selectbox("Serie para la ficha", [None, *(cell["id"] for cell in cells)],
                           format_func=lambda key: key or "Promedio del sector", key=f"cell_{region}")
    card = evidence_card(region, variable, window_a=window_a, window_b=window_b, cell_id=cell_id) if cell_id else regional
    display_card(card)

    st.subheader("El Niño")
    event = card["enso"]
    if event["months"]:
        st.caption(f"{event['episode']['start']} a {event['episode']['end']} · "
                   f"Climatología mensual 1981–2010 · {display_unit(event['unit'])}")
        st.line_chart(pd.DataFrame(event["months"]).set_index("date")[["value", "normal", "neutral"]].dropna(axis=1, how="all"))
        st.dataframe(event["months"], hide_index=True)
        if event["status"] == "neutral_unverified":
            st.info("Período neutral anterior pendiente de verificación con el IMN.")
        else:
            st.caption(f"Referencia neutral documentada: {event['neutral_window'][0]} a {event['neutral_window'][1]}.")
            for index, url in enumerate(event["neutral_sources"], 1):
                st.markdown(f"[Referencia neutral del IMN {index}]({url})")
        for index, url in enumerate(event["episode"]["sources"], 1):
            st.markdown(f"[Documento del IMN {index}]({url})")
        key = "enso_mean_vs_neutral" if event["status"] == "ok" else "enso_mean_anomaly"
        magnitudes = [abs(cell[key]) for cell in cells if cell[key] is not None]
        extent = max(magnitudes, default=0) or 1
        label = "Diferencia media frente al período neutral" if event["status"] == "ok" else "Anomalía media frente a 1981–2010"
        cell_map(cells, key, (-extent, extent), label, display_unit(event["unit"]))

    if variable == "PRECTOTCORR":
        st.subheader("Servicio de agua")
        for row in card["water_coverage"]:
            source = card["water_sources"][row["sourceId"]]
            st.metric(f"{row['geography']} · {row['indicator']} ({row['year']})", f"{row['value']} %")
            st.caption(f"Denominador de {row['denominator']:,} personas. [{source['label']}]({source['url']})")
        if not card["water_coverage"]:
            st.info("Sin indicador verificado para el cantón.")
        for operator in card["water_operators"]:
            source = card["water_sources"].get(operator.get("sourceId"))
            if source:
                st.markdown(f"[{operator['name']}]({source['url']}) · {', '.join(operator['communities'])}")
        for row in card["distribution"]:
            source = card["water_sources"][row["sourceId"]]
            st.write(f"{row['value']} {row['unit']} · {row['indicator']} ({row['year']}). {row['limitation']}")
            st.markdown(f"[{source['label']}]({source['url']})")
        st.caption("Sin series de horas efectivas o volúmenes para este cantón.")

    st.subheader("Pronóstico local experimental")
    forecast = card["forecast"]
    if forecast["status"] == "local_data_pending":
        st.info(forecast["message"])
        st.markdown(f"[Solicitud de datos de estaciones al IMN]({forecast['source_url']})")
    elif forecast["status"] == "station_data_invalid":
        st.info(forecast["message"])
    else:
        st.json(forecast, expanded=False)

    st.subheader("Ficha y descargas")
    for limitation in card["limitations"]:
        st.caption(limitation)
    st.markdown(f"[{card['source']}]({card['sourceUrl']})")
    st.caption("Para imprimir la ficha, usá la opción Imprimir del navegador.")
    st.download_button("Ficha JSON", to_json(card, indent=2), "ficha-aguaalerta.json", "application/json")
    labels = {"series": "Serie anual", "results": "Resultados", "water": "Cobertura de agua",
              "distribution": "Distribución", "sources": "Fuentes", "enso": "El Niño"}
    for table, rows in csv_tables(card).items():
        if rows:
            st.download_button(f"CSV · {labels[table]}", format_csv(rows).encode("utf-8"),
                               f"{table}.csv", "text/csv", key=f"download-{table}")
