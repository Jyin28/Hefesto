"""AguaAlerta contract extensions for F2 (J2.1/J2.3). Owner: Jacky.

[PROPUESTA, pendiente de acuerdo con Samuel/Emanuel/Kevin]. Additive: contracts v2 in
contracts.py are untouched; these types ride next to them via wrappers. Pure stdlib, no I/O.
Field names follow 00_LEEME_JACKY.md sections 3.1 and 3.2.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

EXT_SCHEMA_VERSION = "2.1-proposal"
PRODUCTS = ("historical", "event", "forecast", "water_distribution", "service_coverage")
RESPONSE_PRODUCTS = PRODUCTS + ("capabilities", "data_coverage")
SPATIAL_LEVELS = ("zone", "cell")
TIME_RESOLUTIONS = ("monthly", "annual", "daily")
SUPPORTED_RESOLUTIONS = ("monthly", "annual")
MAP_METRICS = ("slope", "q", "value", "anomaly")
AVAILABILITY_STATUSES = ("available", "partial", "unavailable", "unsupported", "stale", "error")
SOURCE_MODES = ("mock", "real", "mixed", "unknown")
VALIDATION_STATUSES = ("not_evaluated", "validated", "failed")
RECORD_KINDS = ("scheduled", "observed", "corrected")
INDICATOR_IDS = ("household_coverage", "volume_compliance", "continuity", "report_completeness")


@dataclass(frozen=True)
class ZoneSpec:
    zone_id: str
    label: str
    zone_kind: str  # didactic_box | mock_fixture
    bbox: tuple[float, float, float, float]  # west, south, east, north
    crs: str
    zone_version: str
    geometry_sha256: str
    mask_version: str
    mask_sha256: str
    cell_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    geographic_scale: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    grid_id: str
    grid_version: str
    lat: float
    lon: float
    footprint: tuple[float, float, float, float]  # west, south, east, north
    native_resolution: tuple[float, float]  # deg lat, deg lon
    source_ids: tuple[str, ...]
    zone_ids: tuple[str, ...]  # a cell may belong to several zones


@dataclass(frozen=True)
class AnalysisQuery:
    product: str
    variable: str | None
    zone_ids: tuple[str, ...] = ()
    cell_ids: tuple[str, ...] = ()
    spatial_level: str = "zone"
    start_date: str = "1981-01-01"  # inclusive ISO date
    end_date: str = "2024-12-31"  # inclusive ISO date
    time_resolution: str = "annual"
    preset_id: str | None = None
    event_id: str | None = None
    baseline: str | None = None  # "YYYY-YYYY"
    analysis_scope_id: str | None = None
    metric: str | None = None  # map metric: slope | q | value | anomaly (proposed extension)


@dataclass(frozen=True)
class Availability:
    status: str
    reason_code: str | None
    message: str
    missing_requirements: tuple[str, ...]
    available_range: tuple[str, str] | None
    available_resolution: tuple[str, ...]
    checked_at: str
    retryable: bool


@dataclass(frozen=True)
class ServiceResponse:
    """Common envelope. payload is typed per product; null when nothing computable."""

    schema_version: str
    request_id: str
    product: str
    query_requested: dict
    query_effective: dict | None
    result_id: str | None
    availability: Availability
    source_mode: str
    synthetic: bool | None
    payload: Any
    provenance: dict | None
    geographic_context: dict | None
    data_coverage: dict | None
    limitations: tuple[str, ...]
    warnings: tuple[str, ...]
    forecast_metadata: dict | None = None
    distribution_metadata: dict | None = None
    service_coverage_metadata: dict | None = None


@dataclass(frozen=True)
class ForecastPoint:
    valid_time: str
    point_estimate: float | None
    lower: float | None  # null when no interval was estimated
    upper: float | None
    interval_level: float | None
    interval_method: str | None


@dataclass(frozen=True)
class ForecastMetadata:
    forecast_id: str
    model_id: str | None
    model_version: str | None
    target_variable: str
    target_definition: str
    unit: str
    zone_id: str
    effective_scale: str
    issued_at: str | None
    data_cutoff: str | None
    training_start: str | None
    training_end: str | None
    forecast_start: str | None
    forecast_end: str | None
    horizon: str | None
    frequency: str | None
    timezone: str
    valid_until: str | None
    input_source_ids: tuple[str, ...]
    input_hashes: tuple[str, ...]
    config_hash: str | None
    code_version: str
    synthetic: bool
    generation_mode: str  # calculated | imported
    validation_status: str  # not_evaluated | validated | failed
    validation_method: str | None
    evaluation_period: str | None
    sample_count: int | None
    benchmark: str | None
    metric_name: str | None
    metric_value: float | None
    metric_unit: str | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class WaterRecord:
    record_id: str
    source_id: str
    dataset_version: str
    zone_id: str
    service_area_id: str
    geometry_version: str
    period_start: str
    period_end: str
    timezone: str
    record_kind: str  # scheduled | observed | corrected
    event_status: str | None  # e.g. delivered | paused | None
    volume: float | None
    volume_unit: str
    households_served: int | None
    population_served: int | None
    service_duration_hours: float | None
    reporting_completeness: float | None
    updated_at: str
    retrieved_at: str | None
    quality_flags: tuple[str, ...]
    synthetic: bool
    corrects_record_id: str | None
    superseded_by: str | None


@dataclass(frozen=True)
class ServiceIndicator:
    indicator_id: str
    definition: str
    period: str
    zone_id: str
    service_area_id: str
    numerator: float | None
    denominator: float | None
    numerator_unit: str
    denominator_unit: str
    value: float | None
    value_unit: str
    denominator_source: str | None
    dedup_method: str | None
    flags: tuple[str, ...]
    reason_code: str | None


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} debe ser fecha ISO YYYY-MM-DD, recibido {value!r}.") from None
