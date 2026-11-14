import json
import unittest
from datetime import date
from unittest import mock

from src import service_mock_f2 as m
from src.contracts import to_json
from src.contracts_ext import AVAILABILITY_STATUSES, AnalysisQuery


def Q(zone="CR_PN", **kw):
    d = dict(product="historical", variable="T2M", zone_ids=(zone,))
    d.update(kw)
    return AnalysisQuery(**d)


class CatalogTests(unittest.TestCase):
    def test_zones_and_cells(self):
        zones = {z.zone_id: z for z in m.list_zones()}
        self.assertIn("CR_PN", zones)
        self.assertEqual(len(zones["CR_PN"].cell_ids), 5)
        self.assertEqual(zones["MOCK_NODATA"].cell_ids, ())
        self.assertEqual(len(m.list_cells()), 10)
        self.assertEqual(len(m.list_cells("CR_CAR")), 5)

    def test_shared_cells_belong_to_several_zones(self):
        shared = [c for c in m.list_cells() if len(c.zone_ids) > 1]
        self.assertTrue(shared)
        self.assertIn("MOCK_PN_NORTH", shared[0].zone_ids + ("MOCK_PN_NORTH",))

    def test_bad_zone_raises(self):
        with self.assertRaises(ValueError):
            m.list_cells("NOPE")


class ValidationTests(unittest.TestCase):
    def test_malformed_queries_raise(self):
        bad = [
            Q(product="bogus"), Q(zone="NOPE"), Q(variable="X"), Q(start_date="2000-13-01"),
            Q(start_date="2010-01-01", end_date="2000-01-01"), Q(time_resolution="hourly"),
            Q(spatial_level="cell"),  # cell level without cell_ids
            AnalysisQuery("historical", "T2M", zone_ids=("CR_PN",), cell_ids=("G_10.000_-85.625",)),
            Q(baseline="abc"), Q(event_id="NOPE"),
        ]
        for q in bad:
            with self.subTest(q=q):
                with self.assertRaises(ValueError):
                    m.get_series(q)


class AvailabilityStateTests(unittest.TestCase):
    def test_all_six_states_reachable(self):
        got = {
            m.get_series(Q("CR_PN")).availability.status,
            m.get_series(Q("MOCK_PARTIAL")).availability.status,
            m.get_series(Q("MOCK_NODATA")).availability.status,
            m.get_series(Q("MOCK_STALE")).availability.status,
            m.get_series(Q("MOCK_ERROR")).availability.status,
            m.get_series(Q(time_resolution="daily")).availability.status,
        }
        self.assertEqual(got, set(AVAILABILITY_STATUSES))

    def test_no_payload_without_data_and_never_fake_zero(self):
        for z in ("MOCK_NODATA", "MOCK_ERROR"):
            r = m.get_series(Q(z))
            self.assertIsNone(r.payload)
            self.assertIsNone(r.result_id)
            self.assertIsNone(r.provenance)
        self.assertTrue(m.get_series(Q("MOCK_ERROR")).availability.retryable)

    def test_partial_truncates_window_and_reports_missing(self):
        r = m.get_series(Q("MOCK_PARTIAL"))
        self.assertEqual(r.query_effective["end_date"], "2010-12-31")
        self.assertEqual(r.query_requested["end_date"], "2024-12-31")
        self.assertEqual(max(x["year"] for x in r.payload), 2010)
        self.assertTrue(r.data_coverage["missing_periods"])
        self.assertIn("window_truncated", r.availability.reason_code)

    def test_stale_keeps_payload_but_flags(self):
        r = m.get_series(Q("MOCK_STALE"))
        self.assertEqual(r.availability.status, "stale")
        self.assertIsNotNone(r.payload)
        self.assertIn("snapshot_expired", r.warnings)

    def test_out_of_coverage_is_unavailable_not_error(self):
        r = m.get_series(Q(start_date="1950-01-01", end_date="1960-12-31"))
        self.assertEqual(r.availability.status, "unavailable")
        self.assertEqual(r.availability.reason_code, "out_of_coverage")

    def test_wrong_product_unsupported(self):
        r = m.get_series(Q(product="event", event_id="EL_NINO_1997_98"))
        self.assertEqual(r.availability.status, "unsupported")


class EnvelopeTests(unittest.TestCase):
    def test_always_mock_synthetic_and_strict_json(self):
        for q in (Q("CR_PN"), Q("MOCK_NODATA"), Q("MOCK_ERROR")):
            r = m.get_series(q)
            self.assertEqual((r.source_mode, r.synthetic), ("mock", True))
            self.assertIsNone(r.forecast_metadata)
            json.loads(to_json(r))  # strict: raises on NaN/Infinity

    def test_result_id_deterministic_and_sensitive(self):
        a, b = m.get_series(Q()), m.get_series(Q())
        self.assertEqual(a.result_id, b.result_id)
        self.assertNotEqual(a.result_id, m.get_series(Q(variable="PRECTOTCORR")).result_id)
        self.assertNotEqual(a.result_id, m.get_series(Q(end_date="2020-12-31")).result_id)


class SeriesTests(unittest.TestCase):
    def test_annual_matches_v2_mock_for_region(self):
        r = m.get_series(Q("CR_PN", start_date="2000-01-01", end_date="2005-12-31"))
        from src import service_mock as base
        v2 = base.get_annual_series("T2M", "CR_PN", 2000, 2005)
        self.assertEqual([x["value"] for x in r.payload], [x["value"] for x in v2])
        self.assertTrue(all(x["complete"] and x["months_valid"] == 12 for x in r.payload))

    def test_partial_year_marked_incomplete_not_filled(self):
        r = m.get_series(Q(start_date="2000-07-01", end_date="2002-12-31"))
        first = r.payload[0]
        self.assertEqual((first["year"], first["months_valid"], first["complete"]), (2000, 6, False))

    def test_monthly_and_cell_level(self):
        r = m.get_series(AnalysisQuery("historical", "T2M", cell_ids=("G_10.000_-85.625",),
                                       spatial_level="cell", time_resolution="monthly",
                                       start_date="2000-01-01", end_date="2000-12-31"))
        self.assertEqual(len(r.payload), 12)
        self.assertEqual(r.payload[0]["cell_id"], "G_10.000_-85.625")
        self.assertEqual(r.payload[0]["unit"], "degC")

    def test_capabilities_per_product(self):
        caps = m.get_capabilities(Q("MOCK_PARTIAL")).payload
        self.assertEqual(set(caps), set(m.PRODUCTS))
        self.assertEqual(caps["historical"]["status"], "partial")
        self.assertEqual(caps["forecast"]["status"], "unavailable")
        self.assertNotEqual(caps["forecast"]["reason_code"], "mock_product_pending")
        self.assertEqual(m.get_capabilities(Q("MOCK_NODATA")).payload["event"]["status"], "unavailable")

    def test_data_coverage(self):
        r = m.get_data_coverage(Q("MOCK_PARTIAL"))
        self.assertEqual(r.payload["valid_months"], 30 * 12)
        self.assertEqual(r.payload["expected_months"], 44 * 12)


class MapTests(unittest.TestCase):
    def test_map_dedups_shared_cells(self):
        r = m.get_map(Q("CR_PN", zone_ids=("CR_PN", "MOCK_PN_NORTH"), metric="slope"))
        ids = [c["cell_id"] for c in r.payload["cells"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 5)
        c = r.payload["cells"][0]
        for k in ("cell_id", "footprint", "metric", "unit", "q_value", "n_years"):
            self.assertIn(k, c)
        self.assertEqual(r.payload["correction"]["method"], "fdr_by")

    def test_map_metrics(self):
        self.assertEqual(m.get_map(Q(metric="q")).payload["cells"][0]["unit"], "probability")
        self.assertEqual(m.get_map(Q(metric="anomaly")).availability.status, "unsupported")

    def test_map_nodata(self):
        self.assertEqual(m.get_map(Q("MOCK_NODATA")).availability.status, "unavailable")


class EventTests(unittest.TestCase):
    def ev(self, **kw):
        d = dict(product="event", variable="PRECTOTCORR", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98")
        d.update(kw)
        return m.get_event_series(AnalysisQuery(**d))

    def test_event_window_and_anomaly(self):
        r = self.ev()
        self.assertEqual(len(r.payload), 12)
        self.assertEqual(r.payload[0]["time"], "1997-06-01")
        self.assertEqual(r.payload[-1]["time"], "1998-05-01")
        self.assertEqual(r.payload[0]["baseline_valid_counts"], 30)
        self.assertIsNotNone(r.payload[0]["anomaly"])
        self.assertEqual(r.availability.status, "available")

    def test_short_baseline_nulls_anomaly(self):
        r = self.ev(baseline="1981-1990")
        self.assertEqual(r.availability.status, "partial")
        self.assertIn("baseline_insufficient", r.warnings)
        self.assertTrue(all(x["anomaly"] is None and x["climatology"] is None for x in r.payload))

    def test_event_requires_event_id(self):
        with self.assertRaises(ValueError):
            m.get_event_series(AnalysisQuery("event", "T2M", zone_ids=("CR_PN",)))


def FQ(zone="CR_PN", variable="T2M", **kw):
    d = dict(product="forecast", variable=variable, zone_ids=(zone,),
             start_date="2025-01-01", end_date="2025-06-30")
    d.update(kw)
    return AnalysisQuery(**d)


def WQ(product="water_distribution", zones=("CR_PN",), **kw):
    d = dict(product=product, variable=None, zone_ids=zones, start_date="2024-01-01", end_date="2024-06-30")
    d.update(kw)
    return AnalysisQuery(**d)


class ForecastTests(unittest.TestCase):
    def test_five_zone_cases(self):
        expect = {
            "CR_PN": ("available", None),
            "CR_CAR": ("unavailable", "forecast_not_validated"),
            "MOCK_PN_NORTH": ("unavailable", "forecast_validation_failed"),
            "MOCK_STALE": ("stale", "forecast_expired"),
            "MOCK_PARTIAL": ("unavailable", "no_forecast_model"),
        }
        for z, (status, reason) in expect.items():
            with self.subTest(zone=z):
                r = m.get_local_forecast(FQ(z))
                self.assertEqual((r.availability.status, r.availability.reason_code), (status, reason))
                json.loads(to_json(r))

    def test_unvalidated_has_metadata_but_no_predictions(self):
        r = m.get_local_forecast(FQ("CR_CAR"))
        self.assertIsNone(r.payload)
        self.assertEqual(r.forecast_metadata["validation_status"], "not_evaluated")
        self.assertIsNone(r.result_id)

    def test_validated_payload_and_metadata(self):
        r = m.get_local_forecast(FQ("CR_PN"))
        self.assertEqual(len(r.payload), 6)
        self.assertEqual(r.forecast_metadata["validation_status"], "validated")
        self.assertEqual(r.forecast_metadata["valid_until"], "2030-12-31")
        self.assertTrue(r.synthetic)
        self.assertIsNotNone(r.payload[0]["lower"])

    def test_no_interval_is_null_with_warning(self):
        r = m.get_local_forecast(FQ("CR_PN", "PRECTOTCORR"))
        self.assertIsNone(r.payload[0]["lower"])
        self.assertIsNone(r.payload[0]["interval_method"])
        self.assertIn("interval_not_estimated", r.warnings)

    def test_expiry_uses_injectable_clock(self):
        with mock.patch.object(m, "_today", return_value=date(2031, 1, 1)):
            r = m.get_local_forecast(FQ("CR_PN"))
        self.assertEqual(r.availability.status, "stale")
        self.assertIsNotNone(r.payload)  # issue date untouched, payload still served
        self.assertEqual(r.forecast_metadata["issued_at"], "2025-01-01T00:00:00Z")

    def test_window_handling(self):
        part = m.get_local_forecast(FQ("CR_PN", end_date="2025-12-31"))
        self.assertEqual(part.availability.status, "partial")
        self.assertEqual(part.query_effective["end_date"], "2025-06-30")
        out = m.get_local_forecast(FQ("CR_PN", start_date="2030-01-01", end_date="2030-12-31"))
        self.assertEqual(out.availability.reason_code, "out_of_forecast_range")

    def test_unsupported_paths(self):
        cell = AnalysisQuery("forecast", "T2M", cell_ids=("G_10.000_-85.625",), spatial_level="cell",
                             start_date="2025-01-01", end_date="2025-06-30")
        self.assertEqual(m.get_local_forecast(cell).availability.reason_code, "forecast_cell_not_supported")
        multi = FQ(zone_ids=("CR_PN", "CR_CAR"))
        self.assertEqual(m.get_local_forecast(multi).availability.reason_code, "forecast_single_zone_only")
        self.assertEqual(m.get_local_forecast(FQ(time_resolution="daily")).availability.status, "unsupported")
        self.assertEqual(m.get_local_forecast(FQ(product="historical")).availability.reason_code, "wrong_product")

    def test_no_trend_extrapolation_without_model(self):
        r = m.get_local_forecast(FQ("MOCK_PARTIAL"))
        self.assertIsNone(r.payload)


class WaterTests(unittest.TestCase):
    def test_scheduled_and_observed_are_separate_records(self):
        r = m.get_water_distribution(WQ())
        kinds = {x["record_kind"] for x in r.payload["records"]}
        self.assertEqual(kinds, {"scheduled", "observed", "corrected"})
        self.assertEqual(r.distribution_metadata["crosswalk"]["zones"], {"CR_PN": "SA_PN_01"})

    def test_correction_not_double_counted(self):
        r = m.get_water_distribution(WQ())
        recs = {x["record_id"]: x for x in r.payload["records"]}
        orig, corr = recs["W_CR_PN_202403_o"], recs["W_CR_PN_202403_c"]
        self.assertEqual(orig["superseded_by"], corr["record_id"])
        self.assertEqual(corr["corrects_record_id"], orig["record_id"])
        march = next(p for p in r.payload["periods"] if p["period"] == "2024-03")
        self.assertEqual(march["observed_volume"], corr["volume"])
        self.assertEqual(march["observed_record_id"], corr["record_id"])

    def test_pause_zero_and_no_report_are_distinct(self):
        r = m.get_water_distribution(WQ())
        by = {p["period"]: p for p in r.payload["periods"]}
        self.assertEqual((by["2024-04"]["report_state"], by["2024-04"]["observed_volume"]), ("paused", 0.0))
        self.assertEqual((by["2024-05"]["report_state"], by["2024-05"]["observed_volume"]), ("not_reported", None))
        self.assertEqual(by["2024-01"]["report_state"], "reported")

    def test_variable_must_be_none(self):
        with self.assertRaises(ValueError):
            m.get_water_distribution(WQ(variable="T2M"))

    def test_zones_without_records(self):
        self.assertEqual(m.get_water_distribution(WQ(zones=("MOCK_PARTIAL",))).availability.reason_code,
                         "no_water_records")
        mixed = m.get_water_distribution(WQ(zones=("CR_PN", "MOCK_PARTIAL")))
        self.assertEqual(mixed.availability.status, "partial")
        self.assertIn("MOCK_PARTIAL", mixed.availability.missing_requirements)
        self.assertEqual(m.get_water_distribution(WQ(zones=("MOCK_ERROR",))).availability.status, "error")

    def test_window_truncated_and_out_of_range(self):
        t = m.get_water_distribution(WQ(end_date="2024-12-31"))
        self.assertEqual(t.availability.status, "partial")
        o = m.get_water_distribution(WQ(start_date="2020-01-01", end_date="2020-12-31"))
        self.assertEqual(o.availability.reason_code, "out_of_water_range")
        self.assertIsNone(o.payload)

    def test_strict_json_and_cell_unsupported(self):
        json.loads(to_json(m.get_water_distribution(WQ())))
        c = AnalysisQuery("water_distribution", None, cell_ids=("G_10.000_-85.625",), spatial_level="cell")
        self.assertEqual(m.get_water_distribution(c).availability.reason_code, "water_cell_not_supported")


class ServiceCoverageTests(unittest.TestCase):
    def inds(self, r, zone, period):
        return {i["indicator_id"]: i for i in r.payload["indicators"]
                if i["zone_id"] == zone and i["period"] == period}

    def test_values_from_compatible_denominators(self):
        r = m.get_service_coverage(WQ("service_coverage"))
        jan = self.inds(r, "CR_PN", "2024-01")
        self.assertAlmostEqual(jan["volume_compliance"]["value"], 95.0)
        self.assertEqual(jan["household_coverage"]["denominator_source"], "MOCK_PADRON_2024")
        self.assertEqual(jan["volume_compliance"]["value_unit"], "percent")

    def test_missing_denominator_is_null_and_partial(self):
        r = m.get_service_coverage(WQ("service_coverage", ("CR_CAR",)))
        hh = self.inds(r, "CR_CAR", "2024-01")["household_coverage"]
        self.assertIsNone(hh["value"])
        self.assertEqual(hh["reason_code"], "denominator_missing")
        self.assertEqual(r.availability.status, "partial")
        self.assertEqual(r.availability.reason_code, "denominator_missing")

    def test_over_100_kept_with_flag_never_clipped(self):
        jun = self.inds(m.get_service_coverage(WQ("service_coverage")), "CR_PN", "2024-06")
        self.assertAlmostEqual(jun["volume_compliance"]["value"], 110.0)
        self.assertIn("exceeds_100", jun["volume_compliance"]["flags"])

    def test_pause_and_no_report_semantics(self):
        r = m.get_service_coverage(WQ("service_coverage"))
        apr, may = self.inds(r, "CR_PN", "2024-04"), self.inds(r, "CR_PN", "2024-05")
        self.assertEqual(apr["volume_compliance"]["value"], 0.0)
        self.assertIn("paused", apr["volume_compliance"]["flags"])
        self.assertIsNone(may["volume_compliance"]["value"])
        self.assertEqual(may["volume_compliance"]["reason_code"], "not_reported")
        self.assertEqual(may["report_completeness"]["value"], 0.0)
        self.assertIn("months_not_reported", r.warnings)

    def test_no_cross_zone_average(self):
        r = m.get_service_coverage(WQ("service_coverage", ("CR_PN", "CR_CAR")))
        self.assertIn("no_cross_zone_average", r.warnings)
        self.assertIsNone(r.service_coverage_metadata["cross_zone_average"])
        self.assertTrue(all(i["zone_id"] in ("CR_PN", "CR_CAR") for i in r.payload["indicators"]))
        json.loads(to_json(r))

    def test_not_derived_from_rainfall(self):
        r = m.get_service_coverage(WQ("service_coverage", variable=None))
        self.assertEqual(r.product, "service_coverage")
        with self.assertRaises(ValueError):
            m.get_service_coverage(WQ("service_coverage", variable="PRECTOTCORR"))

    def test_capabilities_probe_new_products(self):
        caps = m.get_capabilities(Q("CR_PN")).payload
        self.assertEqual(caps["forecast"]["status"], "available")
        self.assertEqual(caps["water_distribution"]["status"], "available")
        self.assertEqual(m.get_capabilities(Q("CR_CAR")).payload["service_coverage"]["status"], "partial")


if __name__ == "__main__":
    unittest.main()
