# Plantillas deterministas de `summary` — Ficha de Detective

Textos fijos para `build_evidence_card()`. Placeholders: `{variable_label}`, `{region_name}`, `{start_year}`, `{end_year}`, `{n_years}`, `{slope_per_decade}`, `{slope_unit}`, `{p_adjusted}`.

`{slope_per_decade}` se muestra con signo (positivo = aumento, negativo = disminución). No se calculan ni se inventan valores fuera de estos placeholders.

## A) `level == "inferential"` y `significant == True`

```text
Entre {start_year} y {end_year} ({n_years} años consecutivos), {variable_label} en {region_name} cambió {slope_per_decade} {slope_unit} por década. Esta tendencia lineal es estadísticamente significativa y sobrevive a la corrección Benjamini-Yekutieli (valor p ajustado = {p_adjusted}). Describe lo ocurrido en estos datos de reanálisis a escala regional (decenas de km): no demuestra causas ni pronostica el futuro. Uso exclusivamente educativo.
```

## B) `level == "inferential"` y `significant == False`

```text
Entre {start_year} y {end_year} ({n_years} años consecutivos), la pendiente de {variable_label} en {region_name} fue de {slope_per_decade} {slope_unit} por década, pero no es estadísticamente significativa tras la corrección Benjamini-Yekutieli (valor p ajustado = {p_adjusted}). "No significativo" significa evidencia insuficiente bajo este modelo; NO significa ausencia de cambio. Agregar más años no garantiza que el valor p disminuya. Uso exclusivamente educativo.
```

## C) `level == "descriptive"` por duración (`10 <= n_years <= 29`)

```text
Entre {start_year} y {end_year} ({n_years} años), la pendiente descriptiva de {variable_label} en {region_name} fue de {slope_per_decade} {slope_unit} por década. Con menos de 30 años consecutivos no se calcula valor p ni intervalo de confianza, por lo que esta cifra solo resume los datos disponibles y no establece si la tendencia es estadísticamente real. Uso exclusivamente educativo.
```

## D) `level == "descriptive"` por `temporal_gaps` o `insufficient_data`

### D1) `temporal_gaps` (huecos internos)

```text
Los datos de {variable_label} en {region_name} entre {start_year} y {end_year} tienen años faltantes en medio de la serie ({n_years} años con datos completos). La pendiente descriptiva calculada con los años reales es de {slope_per_decade} {slope_unit} por década. No se comprimen los años faltantes y no se calcula valor p inferencial. Uso exclusivamente educativo.
```

### D2) `insufficient_data` (`n_years < 10`)

```text
Los datos de {variable_label} en {region_name} entre {start_year} y {end_year} cubren solo {n_years} años completos, menos de los 10 necesarios. No se ajusta ninguna tendencia ni se calcula valor p. Uso exclusivamente educativo.
```
