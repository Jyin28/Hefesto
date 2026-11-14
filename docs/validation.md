# Hefesto · Estado y validación de Detective Tico

Revisión de GitHub del 14 de noviembre de 2026.

| Integrante | Aportes encontrados | Pendientes para cerrar |
|---|---|---|
| Emanuel | [Fase 1 en rama](https://github.com/Jyin28/Hefesto/tree/emanuel/fase1-decisiones-fixtures) y [plan del MVP](https://github.com/Jyin28/Hefesto/tree/docs/plan-detective-tico). Preparación mensual/anual, ciencia y adaptador real en la rama local de fase 2. | Integrar por PR, validar con Diego y evaluar el pronóstico con datos de estación. |
| Samuel | [PR #3 en main](https://github.com/Jyin28/Hefesto/pull/3), NASA POWER mensual 1981–2024, Parquet, máscaras, procedencia y QA. [Rama de Samuel](https://github.com/Jyin28/Hefesto/tree/feat/samuel-data-cr) con cajas regionales GeoJSON. | Descargar y validar los polígonos cantonales vigentes del IGN, confirmar condiciones de uso, aportar datos históricos de estaciones y registros operativos del agua. |
| Jacky | [PR #6 en main](https://github.com/Jyin28/Hefesto/pull/6), contrato v2 y mock. [PR #7](https://github.com/Jyin28/Hefesto/pull/7) incorporado a la rama del #6, con mock de cinco productos, caché, exportación y 14 ejemplos. | Llevar el #7 a main, revisar el adaptador real de esta rama y acordar los consumidores del contrato 2.1 propuesto. |
| Kevin | [PR #4 en main](https://github.com/Jyin28/Hefesto/pull/4), interfaz base de Streamlit, asistente guiado y mock. | Verificar ambos recorridos con datos reales en móvil y escritorio, incluyendo mapas, descarga e impresión. |
| Joshua | [PR #5 en main](https://github.com/Jyin28/Hefesto/pull/5), narrativa, glosario, afirmaciones, pitch, video y acuerdo de equipo. | Revisar las cifras y capturas finales, confirmar el aviso con la ASADA y grabar el video. |
| Diego | QA y release según el acuerdo. No se encontró una rama, PR o commit atribuible a Diego entre los visibles en GitHub. | Cotejar HAC con statsmodels, validar la web en otro equipo y comprobar la URL pública en una ventana privada. Incorporar su matriz de QA si existe fuera de GitHub. |

El remoto reportó main en 247ac7d. El merge del PR #7 está en 0840223 sobre feat/jacky-f1-contracts-complete. La rama local retoma la interfaz de Kevin desde el historial disponible y conserva su asistente con HEFESTO_USE_MOCK=1. Streamlit, React y la API de esta rama consumen el mismo cálculo real.

## Estado por entrega

| Entrega | Implementado y comprobable | Pendiente |
|---|---|---|
| 1. Datos y catálogo | NASA POWER real, 10 celdas, catálogo de 84 cantones de la DTA 2026, fechas del IMN, dos indicadores de AyA, directorio piloto de Santa Cruz y horario comunitario programado. | Verificación de polígonos del IGN, condiciones de publicación y más registros observados y áreas de servicio. |
| 2. Comparación y ciencia | Preparación, ventanas A y B, OLS/HAC, BY por familias, Sen/Mann–Kendall, El Niño, huellas SHA-256 y consulta real. | Revisión de las decisiones de cobertura, confirmación independiente con statsmodels y conciliación con el contrato propuesto por Jacky. |
| 3. Web y relato | Implementación de calor y lluvia en Streamlit y React, ficha, CSV y JSON y cifras para el relato. | Revisión visual de ambas interfaces, capturas y video. |
| 4. Pronóstico | Evaluador con expansión cronológica y climatología de estación. Estado explícito de datos pendientes. | Serie local continua, permiso, ubicación, unidades y QA. La validación exige 10 años iniciales y 24 meses de evaluación. El sitio solo devuelve una predicción si el modelo mejora el MAE de climatología y el mes objetivo sigue vigente. |
| 5. Demostración | Generación de snapshot, pruebas de cálculo y de consistencia de exportación. | Arranque en limpio con dependencias, aceptación en navegador y URL pública. |

## Resultados para el guion

NASA POWER 1981–2024, diez celdas nativas en dos sectores. B − A compara 2003–2024 con 1981–2002. El IC del 95 % es individual. BY regional usa las cuatro consultas; en el mapa, cada variable usa su familia de celdas.

| Sector y variable | Diferencia de promedios B − A | Pendiente por década | IC individual 95 % | p ajustado BY |
|---|---:|---:|---:|---:|
| Pacífico Norte · temperatura | −0,182 °C | −0,0365 °C/década | [−0,1434, 0,0705] | 1,000 |
| Caribe · temperatura | +0,277 °C | +0,1440 °C/década | [0,0811, 0,2069] | 0,000102 |
| Pacífico Norte · lluvia | +995,10 mm/año | +401,61 mm/año por década | [255,25, 547,97] | 0,0000153 |
| Caribe · lluvia | +1.275,19 mm/año | +592,14 mm/año por década | [366,36, 817,91] | 0,0000171 |

Para calor, mostrar primero Caribe, donde los métodos coinciden en evidencia al 5 %, y después Pacífico Norte, donde el IC individual incluye cero. Para lluvia, distinguir el cambio entre ventanas de la pendiente de largo plazo y mostrar El Niño de julio de 2023 a abril de 2024. La ventana neutral identificada es julio de 2013 a abril de 2014. Las anomalías se refieren a 1981–2010, por mes calendario, con un mínimo de 24 observaciones para la referencia mensual.

La ventana neutral se elige entre períodos documentados del catálogo. El IMN registró El Niño Modoki en julio de 2019 y La Niña de septiembre de 2017 a abril de 2018. Los boletines de julio de 2013, enero de 2014 y abril de 2014 respaldan la referencia elegida. Al ampliar el catálogo, el servicio toma automáticamente la opción previa más cercana que cubra los mismos meses.

- [IMN · Julio de 2019](https://www.imn.ac.cr/documents/10179/470467/%23123)
- [IMN · Julio de 2018 y el episodio de La Niña 2017–2018](https://www.imn.ac.cr/documents/10179/454290/JULIO)

AyA / LNA estimó 73 % de población con agua potable en Santa Cruz y 90 % en Limón en 2020. Sus denominadores son 69.424 y 99.041 habitantes. La programación de Playa Grande se muestra a escala comunitaria con sus fechas y fuente. Son horas programadas. Para saber la situación efectiva se requiere información operativa de la ASADA.

## Validación local y demostración

```powershell
python -m unittest tests.test_contracts_mock tests.test_prepare tests.test_statistics tests.test_detective_tico
python tests/fixtures/stats/generate_and_verify.py
python -m src.web_data
```

Se verificaron SHA-256 y unidades de los dos archivos NASA POWER. Hay 10.560 registros mensuales para las dos variables, 33 ceros, 880 años-celda y 176 años-región completos. En 2000 se obtienen 26,33 °C y 866,02 mm en Pacífico Norte y 21,70 °C y 1.847,00 mm en Caribe. La prueba independiente comprueba acumulación en una celda bisiesta y HAC mediante la matriz sándwich.

La prueba de Parquet necesita numpy, pandas y pyarrow. Las descargas de Python, npm y cartografía fallaron por DNS. Se verificó sintaxis TypeScript/TSX. Quedan la compilación completa y el navegador. Para la aceptación, seguir el README, abrir ambos recorridos, cambiar zona, celda, variable y ventanas, comparar JSON y CSV y comprobar el enlace público desde una ventana privada.

### Pronóstico y entrada de estaciones

Guardar data/local/CR_CAR_T2M.json o data/local/CR_PN_PRECTOTCORR.json, según región y variable. El objeto contiene metadata con station_id, name, latitude, longitude, source_url, license, unit y records con year, month y value. Unidades degC y mm/month. El evaluador exige que el tramo admitido sea continuo y conserva los datos de origen. La estación de Puerto Limón en ClimatView tiene observaciones con huecos recientes.

- [IMN · Solicitud de servicios](https://imn.ac.cr/solicitud-de-servicios)
- [ClimatView · Puerto Limón](https://ds.data.jma.go.jp/tcc/tcc/products/climate/climatview/graph_mkhtml.php?m=10&n=78767&y=2026)
