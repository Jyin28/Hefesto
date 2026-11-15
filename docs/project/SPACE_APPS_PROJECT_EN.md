# Hefesto — Space Apps Project Submission

## 1. Project name

**Hefesto: AguaAlerta: Monitoring Water Supply Risks During El Niño**

**Tagline:** Connecting ASADAs and communities with local water information and El Niño risk notices.

**Team:** Hefesto

## 2. Project summary

Hefesto: AguaAlerta is designed for both ASADA administrators and the general public in Costa Rica, with a focus on the effects of El Niño on community water systems. The platform aims to simplify administrators' collection of water-flow records and display updated information in real time as reports arrive. Members of the public will be able to explore information about any area of interest and subscribe to selected zones through Telegram to receive relevant notices and warnings. By combining local records with NASA POWER climate data and geographic context, we aim to identify patterns and develop predictions of potential water-supply risks. Our goal is to make administrators' work easier while giving communities accessible information about their chosen locations. The current prototype includes climate maps, a water-operator directory, and browser-based reporting demonstrations. Shared real-time reporting, validated flow predictions, and Telegram subscriptions and notification delivery remain development objectives.

## 3. Detailed project description

### The problem

Our project focuses on how the effects of El Niño affect Costa Rica's community water systems and the people who depend on them. ASADA administrators need a practical way to collect flow measurements, review changes in their water sources, and communicate possible supply risks to their communities. Hefesto addresses the task of bringing those local reports together and making them useful for monitoring, analysis, and communication.

The central problem we aim to solve is the effort required to turn administrator reports into timely, understandable information that is useful to both water operators and the public. Our goal is to streamline that process so administrators can spend less time organizing records, while anyone can consult information about a location of interest and stay informed about relevant changes.

### Our objective and intended users

Hefesto is designed for two user groups: **ASADA administrators** and **the general public**. Administrators will submit water-flow records through a consistent reporting process, review updated information in a shared dashboard, and communicate notices about the systems they manage.

Members of the public will be able to access the website, search for or select any zone of interest, and consult the available climate, water-system, and notice information for that location. They will also be able to subscribe to one or more selected zones through Telegram and receive notices and warnings relevant to those subscriptions. Public access to information is part of the intended experience and does not require an administrator role.

Our objective connects administrator reporting with public access: simplify data collection, visualize reported flows in real time, analyze the collected records to identify and predict patterns, let people explore information by zone, and deliver relevant notices through Telegram subscriptions. NASA climate data provides historical environmental context for this workflow; locally reported flow measurements provide the information about each water system.

### The intended reporting and communication workflow

- **Collect:** administrators enter flow measurements and relevant observations for their ASADA. The proposed records should identify the water source, measurement time, unit, and reporting operator so updates remain traceable.
- **Visualize:** shared views update as reports arrive, allowing administrators to monitor their systems and the public to consult the latest available information for a selected zone. Real-time visualization refers to displaying newly submitted reports promptly; it does not imply that every water source has a continuously connected sensor.
- **Analyze and predict:** the platform is intended to examine the collected flow histories alongside climate context, identify unusual changes and recurring patterns, and develop predictions of potential supply risks. Predictive performance must be evaluated against local measurements before these outputs can support operational decisions.
- **Explore and subscribe:** anyone should be able to search for a zone, consult its available information, and select one or more zones to follow through Telegram. Subscribers should be able to change or cancel their subscriptions.
- **Inform and warn:** administrators should be able to publish notices and warnings for the communities they serve. The planned Telegram integration will deliver relevant messages to people subscribed to the affected zones. Notices should identify the area, source, and issue time, and distinguish an administrator's service notice from a model-based risk estimate.

This workflow is the intended product direction. Shared reporting infrastructure, validated flow predictions, and Telegram subscriptions and automated message delivery are not yet demonstrated by the reviewed repository.

### What the current prototype provides

The React web prototype provides a starting point for both user groups: maps, geographic navigation, and a searchable directory of water operators support public exploration, while demonstration forms support administrator reporting of flow and perceived El Niño effects. Reports are currently stored in the user's browser. They are not synchronized across administrators or devices through a shared production service, and the reviewed implementation does not establish a working Telegram subscription and notification service.

The interface also includes three map views:

- **NASA POWER:** historical temperature, annual rainfall, relative humidity, and UV layers. Temperature, rainfall, and humidity cover 1981–2024; UV begins in 2001.
- **Copernicus Climate Data Store:** temperature, rainfall, and derived relative humidity from the bundled ERA5-Land dataset.
- **National data:** cantonal geography, waterways, and water-operator information, including ASADAs.

The repository also includes a Streamlit climate explorer that compares historical conditions in the North Pacific and Caribbean study sectors. It provides series, maps, statistical diagnostics, an El Niño study window, and downloadable reports. This existing analysis provides supporting climate context for the ASADA-focused platform; it does not yet predict an individual ASADA's flow.

### The role of NASA data and local measurements

NASA POWER supplies a historical reference for investigating rainfall and temperature patterns around El Niño episodes and over longer periods. The guided analysis uses ten selected native climate cells, five per study sector, covering January 1981 through December 2024. Original NASA responses, source metadata, and checksums are retained for traceability.

Annual temperature is a day-weighted average. Annual rainfall is calculated by multiplying monthly mean daily precipitation by the number of days in each month and summing the results. Only years with twelve valid months enter the annual analysis. Eligible historical trend analyses include uncertainty estimates and correction for multiple testing; shorter series are treated descriptively.

These climate records complement local reports. They do not measure ASADA flow or establish how much drinking water is available. The proposed flow analysis must use administrator measurements with their dates, units, and geographic scope. An observed change during an El Niño episode does not by itself establish that El Niño caused it.

### Expected value and next steps

Hefesto aims to make administrators' work easier by bringing reporting, visualization, analysis, and communication into one workflow. For the general public, the intended value is direct access to information about chosen zones and relevant Telegram updates without repeatedly checking the website. Together, these capabilities aim to improve access to recent records, understanding of changes in flow, and communication about possible risks. These are project goals; time savings and service improvements have not yet been measured with users.

The next development steps are to connect reporting to a shared database and authenticated administrator accounts, implement updates across devices, collect consistent local flow histories, evaluate predictive models, and add Telegram subscriptions and notification delivery by zone. Testing should include both ASADA administrators and members of the public: whether reporting becomes easier, whether people can find and understand information for their chosen areas, and whether subscribers receive relevant notices.

### Current maturity and limitations

The current implementation is a prototype. Its demonstration accounts and browser-local reports do not provide a production real-time monitoring network. The climate interface contains trend extrapolations and illustrative alert categories, while the separate station-based forecast component is awaiting local data. Neither is a validated forecast of ASADA flow or water-supply disruption. Telegram zone subscriptions and automated community warning delivery are planned capabilities, not established functions of the reviewed implementation.

NASA POWER's meteorological fields are regional reanalysis estimates, not local station measurements. Their coarse grid smooths coastlines and mountainous terrain; rainfall trends have not been validated against local rain gauges. The existing prototype is therefore not ready for operational emergency or rationing decisions. Administrator testing, local-data validation, and reliable reporting and notification infrastructure are required to reach the intended service.

## 4. NASA data used

**Primary service:** NASA POWER — Prediction Of Worldwide Energy Resources, Monthly and Annual Regional API. [1]

| NASA parameter | Meaning and units | Period included | Role in Hefesto |
|---|---|---|---|
| `T2M` | Air temperature at 2 meters, °C | 1981–2024 | Historical series, regional comparisons, temperature maps, and trends. |
| `PRECTOTCORR` | Corrected precipitation, mm/day in the monthly source; converted to mm/year for annual totals | 1981–2024 | Rainfall series, regional comparisons, maps, and historical anomalies. |
| `RH2M` | Relative humidity at 2 meters, % | 1981–2024 | Annual humidity layer in the web map. |
| `ALLSKY_SFC_UV_INDEX` | All-sky surface UV index; the source labels its units as `W m-2 x 40` | 2001–2024 | Annual UV layer in the web map. It represents an average including nighttime, not a midday UV forecast. |

The stored temperature and precipitation responses identify **MERRA2** as their source; humidity identifies **MERRA2 and POWER**. These meteorological fields use a native grid of **0.5° latitude × 0.625° longitude**, approximately 55 × 69 km in Costa Rica. NASA's documentation describes POWER meteorological data as model assimilation products. [2]

The stored UV response identifies **SYN1DEG**, associated with NASA's CERES solar data described in the POWER documentation. Its native grid is **1° × 1°**. The web map assigns the nearest UV source point to each display cell, so neighboring cells can share the same UV value. [1]

Original responses are stored in `data/raw/nasa_power_monthly_*.json`. Core provenance is recorded in `data/processed/provenance_base.json`; additional layer provenance accompanies the web snapshot. The national NASA display contains 24 cells selected for land overlap, while the guided two-sector analysis uses ten cells.

**Suggested acknowledgement:** This project uses data from the NASA POWER Project. Meteorological records are based on MERRA-2 as identified in the stored responses, and the UV record is supplied through the SYN1DEG source. Hefesto's analysis and interpretation are the team's own.

## 5. References and other data sources

### NASA and analysis references

1. **NASA POWER. Monthly and Annual API.** Source service and distinction between meteorological and solar products. [Documentation](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/).
2. **NASA POWER. Meteorological Data Sources.** MERRA-2, model assimilation, and native meteorological resolution. [Documentation](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/).
3. **statsmodels. Robust covariance results.** Reference implementation used for checking the project's HAC statistics. [Documentation](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
4. **statsmodels. Multiple hypothesis testing.** Reference for multiple-testing procedures, including Benjamini–Yekutieli. [Documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

### Complementary sources — not NASA datasets

5. **Copernicus Climate Change Service / ECMWF. ERA5-Land monthly averaged data from 1950 to present.** The project uses 1981–2024 data on the distributed 0.1° grid. Temperature and dewpoint are used to derive relative humidity. DOI: **10.24381/cds.68d2bb30**. [Dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means). Attribution: Contains modified Copernicus Climate Change Service information (2026).
6. **OpenStreetMap contributors / Humanitarian OpenStreetMap Team. Costa Rica waterways.** Hydrographic geometry; this layer does not measure river discharge. Attribution: © OpenStreetMap contributors, ODbL. [Copyright and license](https://www.openstreetmap.org/copyright).
7. **AyA / SAGA. “Operadores y Fuentes (Ubicaciones).”** Repository workbook used to prepare the water-operator directory, dated November 11, 2026 in the project metadata. [AyA institutional website](https://www.aya.go.cr).
8. **AyA / Laboratorio Nacional de Aguas. Water and sanitation coverage, 2020.** Source of the selected cantonal service-coverage indicators bundled with the project. [Report](https://www.aya.go.cr/transparenciainst/rendicion_cuentas/planesespecificossectorial/agua%20para%20consumo%20humano%20y%20saneamiento%20en%20costa%20rica%20al%202020_%20brechas%20en%20tiempos%20de%20pandemia.pdf).
9. **ARESEP. Bulletin 47-2023.** Context for water supplied to ASADAs in Santa Cruz; the cited record does not provide measured delivered volume or hours of service. [Source](https://aresep.go.cr/noticias/aresep-detecta-irregularidades-venta-agua/).
10. **Universidad de Costa Rica. “El Niño y La Niña, dos caras de un mismo fenómeno climático” (2023).** Educational ENSO context. [Article](https://www.ucr.ac.cr/noticias/2023/7/12/el-nino-y-la-nina-dos-caras-de-un-mismo-fenomeno-climatico/).
11. **Instituto Meteorológico Nacional. ENSO bulletins.** Episode references are recorded individually in `data/web/enso.json`. [Institutional website](https://www.imn.ac.cr). Verification of the specific 1997–1998 bulletins remains pending in the repository.

Additional local notices and their original links are recorded in `data/web/local.json`. Photography credits and individual image licenses are listed in `THIRD_PARTY.md`. Project source code is MIT-licensed; datasets and images retain their own terms.

## 6. Public project links

| Item | URL or status |
|---|---|
| Source repository | [https://github.com/Jyin28/Hefesto](https://github.com/Jyin28/Hefesto) — taken from the configured Git remote; anonymous public access could not be confirmed during this review. |
| Live application | **Pending:** no deployed public application URL was found in the reviewed repository files. |
| Demonstration video | **Pending:** no public video URL was found in the reviewed repository files. |
| Space Apps team/project page | [https://www.spaceappschallenge.org/2026/find-a-team/hefesto/](https://www.spaceappschallenge.org/2026/find-a-team/hefesto/) |

## 7. Use of artificial intelligence

### AI assistance during development

We used AI coding assistants to support the development of Hefesto AguaAlerta. The repository's AI usage log records Claude Code and Codex contributions on November 14, 2026. ChatGPT and Codex also assisted with preparing and revising this English project documentation on November 15, 2026, incorporating the team's explanations of the problem, intended users, and Telegram subscription concept.

- **Claude Code:** assisted with data contracts, the simulated service, monthly and annual data preparation, tests, and technical documentation. The log also records assistance with the real service, guided Streamlit interface, exports, homogeneity diagnostics, data verification, and packaging. These entries are attributed to work by Jacky and Emanuel.
- **Codex:** assisted Emanuel with integration of real historical series, evidence generation, ENSO analysis, water-coverage information, the experimental forecasting component, exports, and local validation.
- **ChatGPT and Codex for documentation:** helped organize the Space Apps submission, draft and revise the English text, suggest the AguaAlerta name, and generate the editable Word document. Jacky supplied corrections that established the focus on El Niño, ASADA administration, public access by zone, and planned Telegram notifications.

AI assistance is disclosed as a contribution to code and writing. It does not replace the team's responsibility for the final implementation, source attribution, scientific interpretation, and public claims.

### Verification and human review

The repository log records automated unit tests, local calculation and export checks, and comparisons of the historical HAC statistics with statsmodels. Data verification also checks raw-file hashes, monthly coverage, and agreement between NASA source records and the processed dataset. During preparation of this submission, the data-verification script completed successfully and the generated Word file was checked for valid document structure.

These checks help detect implementation and data-processing errors. They do not establish that every AI-assisted change has received independent human review, that the rainfall estimates match local stations, or that the proposed flow predictions and alerts are operationally reliable. The development log explicitly leaves team or independent review pending for several contributions. Jacky's review of the project wording should not be interpreted as scientific validation of the software.

### AI within the application

The reviewed application does not use a generative language model to calculate historical climate results or produce its runtime summaries. Those summaries use deterministic templates and rules; historical statistics and experimental projections are computed by code. The recorded assistance in implementing a forecasting component is not evidence of a deployed or validated AI forecast of ASADA flow.

The planned analysis of administrator-reported flow records, prediction of risk patterns, and Telegram warnings remain development objectives. Any predictive model will require local-data evaluation before operational use. Telegram subscriptions describe a notification channel, not an AI model.

### Data provenance and disclosure record

NASA POWER and the other cited providers supply the environmental datasets used by the prototype. AI-generated text is not treated as a climate observation or an administrator's flow measurement. Synthetic mock data is used for development and testing and must remain distinguishable from real-source results.

The detailed development record is maintained in docs/project/AI_USAGE.md. This disclosure reflects the recorded contributions and the assistance used for this document; it is not a complete archive of prompts or every interaction with an AI tool.

---

## Team appendix — repository evidence and editorial notes

**Reviewed revision:** `bd25c7d6280b5e7662b18f3c2cd43c02d433bcd5` on branch `ui/glass-theme`.

The product serves both ASADA administrators and the general public. Its objective combines simpler administrator flow-data collection, real-time visualization of submitted reports, pattern analysis and prediction, public consultation of information by zone, and Telegram subscriptions for location-relevant notices. The reviewed repository supplies climate exploration and browser-based reporting demonstrations. Shared synchronization, validated ASADA flow predictions, and Telegram subscription and notification delivery remain development work. The Streamlit explorer provides supporting climate-analysis functionality.

| Statement | Repository evidence |
|---|---|
| Guided questions, two sectors, charts, ENSO tab, and downloads | `app.py`, `src/views.py`, `src/export.py` |
| Original NASA variables, periods, and source identifiers | Headers and parameter metadata in the four `data/raw/nasa_power_monthly_*.json` files |
| Ten-cell historical dataset and provenance | `data/processed/provenance_base.json`, `docs/DATA_SOURCES.md`, `scripts/verify_data.py` |
| National NASA layers and 24 display cells | `src/layers.py`, `web/public/data/snapshot.json`, `data/web/national_cells.json` |
| Three bundled Copernicus layers and 505 display cells | `web/public/data/cds.json`, `data/web/cds_cells.json`, `src/cds.py` |
| 1,334 directory entries for water operators | `data/web/asadas.json`, `web/README.md` |
| Forecasts awaiting station data | All six regional/national temperature and rainfall entries in `web/public/data/snapshot.json` have `forecast.status = local_data_pending` |
| Browser projections are extrapolations | `web/src/analysis.ts`, particularly `project()` |
| Demo operator reports use browser-local storage | `web/README.md`, `web/src/asadas.ts` |
| Scientific limitations and outstanding validation | `docs/limitations.md`, `docs/validation.md`, `docs/project/RELEASE.md` |
| AI assistance during development | `docs/project/AI_USAGE.md` |

**Data verification recorded during the repository review:** `scripts/verify_data.py` completed successfully. It checked raw-file hashes, schema, missing values, geographic masks, monthly coverage, equality between the 10,560 processed records and NASA source records, and complete annual series. This is data-pipeline verification, not independent scientific or user validation. The full automated test suite was not rerun for this documentation-only change.

**Submission details still to complete:** public application and video links; anonymous access to the repository and referenced revision; the public source and usage metadata for the cantonal boundary file; and the exact public source link for the SAGA workbook. Do not claim that the optional Copernicus UV layer is loaded: the current bundled `cds.json` contains only temperature, rainfall, and humidity.
