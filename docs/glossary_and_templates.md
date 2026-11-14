# Glosario, guías y plantillas — Hefesto v2 · Detective Tico

Documento de producto y educación para el equipo (Kevin en UI, Jacky en servicio, Emanuel en estadística). Todo el texto es fijo y determinista: no se genera en tiempo de ejecución.

---

## A. Glosario corto para UI (máximo 2 líneas por término)

> ⚠️ **Advertencia visible (mostrar en la UI):** la temperatura del aire **no** es la temperatura del mar, y la lluvia **no** es caudal de ríos ni suministro de agua.

| Término | Definición para estudiantes |
|---|---|
| **T2M** | Temperatura del aire a 2 metros sobre el suelo. Es aire sobre tierra, no temperatura del mar. |
| **PRECTOTCORR** | Precipitación total corregida: lluvia acumulada, que aquí se resume en mm por año (mm/yr). No mide caudal ni agua potable. |
| **Anomalía** | Diferencia mensual entre un valor y lo normal de ese mes en la climatología 1981–2010. Positiva: más alto que lo normal; negativa: más bajo. |
| **Tendencia lineal** | La recta que mejor resume cómo cambia una serie con los años, expresada como tasa de cambio por década. |
| **Valor p** | Medida de qué tan compatible es el resultado con "no hay tendencia". No dice qué tan grande ni qué tan importante es el cambio. |
| **Intervalo de Confianza (95 %)** | Rango de tasas de cambio compatibles con los datos bajo el modelo. Un rango más ancho indica más incertidumbre. |
| **Significancia estadística ajustada (Benjamini-Yekutieli / BY)** | Verificación que corrige por hacer muchas comparaciones a la vez, para evitar falsos hallazgos. "Significativo" significa que sobrevive a esta corrección. |

---

## B. Guías paso a paso

Recorrido educativo de 8 pasos. Aplica igual a ambos casos locales; cambian la pregunta, la variable y las aclaraciones.

### B.1 `CR_HEAT` — Calor (variable `T2M`)

1. **Pregunta cotidiana:** "¿Se ha vuelto más caliente la región donde vivo?"
2. **Hipótesis opcional del estudiante:** escribir qué cree que pasará (por ejemplo, "el aire está más caliente que hace 30 años") antes de ver los datos. Es opcional y no afecta el cálculo.
3. **Selección de sector y ventana:** elegir `CR_PN` (Pacífico Norte) o `CR_CAR` (Caribe) y el rango de años.
4. **Serie anual completa (12 meses):** ver la serie de temperatura del aire a 2 metros con los 12 meses de cada año.
5. **Tasa por década e IC:** leer la tasa de cambio en °C por década con su Intervalo de Confianza (95 %).
6. **Evidencia estadística (HAC L=3 + BY alfa=0.05):** revisar si la tendencia es estadísticamente significativa tras el ajuste BY.
7. **Límites de escala y reanálisis:** recordar que es temperatura del aire sobre tierra (no del mar) y que la escala (~0.5° x 0.625°, decenas de km) no mide fincas ni cantones específicos.
8. **Descarga de Ficha de Detective:** exportar la ficha con el resumen, la tasa, el IC y los límites.

### B.2 `CR_RAIN` — Lluvia (variable `PRECTOTCORR`)

1. **Pregunta cotidiana:** "¿Está cambiando la cantidad de lluvia que cae en mi región?"
2. **Hipótesis opcional del estudiante:** anotar qué espera ver (por ejemplo, "llueve menos que antes"). Es opcional y no afecta el cálculo.
3. **Selección de sector y ventana:** elegir `CR_PN` (Pacífico Norte) o `CR_CAR` (Caribe) y el rango de años.
4. **Serie anual completa (12 meses):** ver la lluvia acumulada anual (mm/yr) construida con los 12 meses de cada año.
5. **Tasa por década e IC:** leer la tasa de cambio en mm/yr por década con su Intervalo de Confianza (95 %).
6. **Evidencia estadística (HAC L=3 + BY alfa=0.05):** revisar si la tendencia es estadísticamente significativa tras el ajuste BY.
7. **Límites de escala y reanálisis:** recordar que la lluvia no mide caudal de ríos, recarga de acuíferos ni agua potable en ASADAS, y que la escala es regional (decenas de km).
8. **Descarga de Ficha de Detective:** exportar la ficha con el resumen, la tasa, el IC y los límites.

---

## C. Plantillas deterministas para `summary` de la Ficha de Detective

Textos fijos para integrar en `build_evidence_card()`. Placeholders disponibles:
`{variable_label}`, `{region_name}`, `{start_year}`, `{end_year}`, `{n_years}`, `{slope_per_decade}`, `{slope_unit}`, `{p_adjusted}`.

`{slope_per_decade}` se muestra con signo: positivo = aumento, negativo = disminución.

### C.1 `level == "inferential"` y `significant == True`

```text
Entre {start_year} y {end_year} ({n_years} años), {variable_label} en {region_name} cambió {slope_per_decade} {slope_unit} por década (signo positivo: aumento; negativo: disminución). Esta tendencia es estadísticamente significativa y sobrevive a la corrección Benjamini-Yekutieli (valor p ajustado = {p_adjusted}). Este resultado describe lo ocurrido en los datos de reanálisis: no explica sus causas ni pronostica el futuro.
```

### C.2 `level == "inferential"` y `significant == False`

```text
Entre {start_year} y {end_year} ({n_years} años), la tendencia de {variable_label} en {region_name} fue de {slope_per_decade} {slope_unit} por década, pero no es estadísticamente significativa tras la corrección Benjamini-Yekutieli (valor p ajustado = {p_adjusted}). "No significativo" significa evidencia insuficiente bajo este modelo; NO significa ausencia de cambio. Agregar más años no garantiza que el valor p disminuya.
```

### C.3 `level == "descriptive"` por longitud (`10 <= n_years <= 29`)

```text
Entre {start_year} y {end_year} ({n_years} años), la pendiente descriptiva de {variable_label} en {region_name} fue de {slope_per_decade} {slope_unit} por década. Como la serie tiene menos de 30 años, no se evalúa significancia estadística: esta cifra solo describe los datos disponibles.
```

### C.4 `temporal_gaps` o `insufficient_data` (`n_years < 10` o huecos internos)

```text
Los datos de {variable_label} en {region_name} entre {start_year} y {end_year} no permiten un análisis de tendencia: la serie tiene {n_years} años válidos y tiene menos de 10 años o presenta huecos internos. No se comprimen los años faltantes y no se calcula un valor p inferencial.
```

> Nota para integración: en C.4 el texto cubre ambos motivos (`n_years < 10` y huecos internos). Si Jacky/Kevin prefieren mensajes separados por motivo, se pueden dividir en dos plantillas sin cambiar el significado.
