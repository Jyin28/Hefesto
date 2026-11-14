"""Real implementation of the regional service consumed by Kevin's v2 UI."""
from .contracts import (
    COVERAGE_END_YEAR, COVERAGE_START_YEAR, REGION_IDS, SCHEMA_VERSION, VARIABLE_IDS,
    to_jsonable, validate_query,
)
from .export import evidence_card
from .regions import MASK_VERSION, REGION_SPECS
from .service_mock import list_variables
from .web_data import _evidence, annual_rows, climate, climate_package


def list_regions():
    return list(REGION_SPECS.values())


def get_coverage():
    return {
        "schema_version": SCHEMA_VERSION, "synthetic": False, "mask_version": MASK_VERSION,
        "start_year": COVERAGE_START_YEAR, "end_year": COVERAGE_END_YEAR,
        "regions": list(REGION_IDS), "variables": list(VARIABLE_IDS),
    }


def get_annual_series(variable, region_id, start_year, end_year):
    validate_query(variable, region_id, start_year, end_year)
    return [dict(row, synthetic=False) for row in annual_rows()
            if row["region_id"] == region_id and row["variable"] == variable
            and start_year <= row["year"] <= end_year]


def get_trend(variable, region_id, start_year, end_year):
    validate_query(variable, region_id, start_year, end_year)
    entries, _ = _evidence(start_year, end_year)
    return entries[region_id, variable]["ols"]


def get_comparison(variable, start_year, end_year, regions=REGION_IDS):
    validate_query(variable, None, start_year, end_year)
    entries, families = _evidence(start_year, end_year)
    for region in regions:
        validate_query(variable, region, start_year, end_year)
    return to_jsonable({
        "schema_version": SCHEMA_VERSION, "synthetic": False, "variable": variable,
        "start_year": start_year, "end_year": end_year,
        "results": [entries[region, variable]["ols"] for region in regions],
        "family_metadata": [families["ols"]],
    })


def get_cell_trends(variable, region_id, start_year, end_year):
    return climate(region_id, variable, start_year, end_year)["cells"]


def get_event_view(variable):
    return {region: climate(region, variable)["enso"] for region in REGION_IDS}


def build_provenance(query):
    return to_jsonable(climate_package()[2])


def build_evidence_card(query, hypothesis=""):
    return {
        "schema_version": SCHEMA_VERSION, "synthetic": False, "hypothesis": hypothesis,
        "selection": to_jsonable(query),
        "regions": [evidence_card(region, query.variable, start=query.start_year, end=query.end_year)
                    for region in query.regions],
    }
