import csv
import io
import json
import unittest

from src import service_mock_f2 as m
from src.contracts_ext import AnalysisQuery
from src.export_f2 import build_evidence_card_ext, build_export

GEN = "2026-11-14T00:00:00Z"


def hq(zone="CR_PN", **kw):
    d = dict(start_date="2000-01-01", end_date="2009-12-31")
    d.update(kw)
    return AnalysisQuery("historical", "T2M", zone_ids=(zone,), **d)


def rows(files, name):
    return list(csv.DictReader(io.StringIO(files[name].decode("utf-8"))))


def manifest(files):
    return json.loads(files["manifest.json"])


class PresentAbsentTests(unittest.TestCase):
    def test_manifest_lists_present_tables(self):
        f = build_export(m.get_series(hq()), generated_at=GEN)
        man = manifest(f)
        self.assertEqual([t["table"] for t in man["tables_present"]], ["series.csv"])
        self.assertEqual(man["tables_present"][0]["rows"], 10)
        self.assertEqual(man["tables_absent"], [])
        self.assertIn("provenance.json", f)
        self.assertEqual(sorted(man["files"]), sorted(f))

    def test_unavailable_has_no_csv_but_lists_absence(self):
        for zone, reason in (("MOCK_NODATA", "no_data_for_zone"), ("MOCK_ERROR", "internal_error")):
            f = build_export(m.get_series(hq(zone)), generated_at=GEN)
            self.assertFalse([n for n in f if n.endswith(".csv")], zone)
            absent = manifest(f)["tables_absent"]
            self.assertEqual((absent[0]["table"], absent[0]["reason_code"]), ("series.csv", reason))
            self.assertNotIn("provenance.json", f)

    def test_forecast_not_validated_has_metadata_but_no_table(self):
        q = AnalysisQuery("forecast", "T2M", zone_ids=("CR_CAR",), start_date="2025-01-01", end_date="2025-06-30")
        f = build_export(m.get_local_forecast(q), generated_at=GEN)
        self.assertNotIn("forecast.csv", f)
        card = json.loads(f["evidence.json"])
        self.assertEqual(card["forecast_metadata"]["validation_status"], "not_evaluated")
        self.assertIsNone(card["results"])

    def test_water_exports_two_tables(self):
        q = AnalysisQuery("water_distribution", None, zone_ids=("CR_PN",), start_date="2024-01-01",
                          end_date="2024-06-30")
        f = build_export(m.get_water_distribution(q), generated_at=GEN)
        self.assertTrue({"water_distribution.csv", "water_records.csv"} <= set(f))
        self.assertEqual(len(rows(f, "water_records.csv")), 12)

    def test_capabilities_json_only(self):
        f = build_export(m.get_capabilities(hq()), generated_at=GEN)
        self.assertFalse([n for n in f if n.endswith(".csv")])
        self.assertEqual(manifest(f)["tables_absent"], [])


class CsvTests(unittest.TestCase):
    def test_every_row_has_result_id_product_and_join_keys(self):
        for resp, name in ((m.get_series(hq()), "series.csv"),
                           (m.get_map(hq(metric="slope", start_date="1981-01-01", end_date="2024-12-31")),
                            "cells.csv")):
            f = build_export(resp, generated_at=GEN)
            rs = rows(f, name)
            self.assertTrue(rs)
            self.assertTrue(all(r["result_id"] == resp.result_id and r["product"] == "historical" for r in rs))
            self.assertEqual(manifest(f)["tables_present"][0]["join_keys"][0], "result_id")

    def test_missing_is_empty_cell_and_booleans_lowercase(self):
        q = AnalysisQuery("forecast", "PRECTOTCORR", zone_ids=("CR_PN",), start_date="2025-01-01",
                          end_date="2025-06-30")
        r = rows(build_export(m.get_local_forecast(q), generated_at=GEN), "forecast.csv")
        self.assertEqual((r[0]["lower"], r[0]["upper"], r[0]["interval_method"]), ("", "", ""))
        self.assertTrue(r[0]["forecast_id"])
        cov = rows(build_export(m.get_service_coverage(AnalysisQuery(
            "service_coverage", None, zone_ids=("CR_CAR",), start_date="2024-01-01", end_date="2024-06-30")),
            generated_at=GEN), "service_coverage.csv")
        hh = next(x for x in cov if x["indicator_id"] == "household_coverage" and x["period"] == "2024-01")
        self.assertEqual((hh["value"], hh["reason_code"]), ("", "denominator_missing"))

    def test_nested_values_are_compact_json(self):
        f = build_export(m.get_map(hq(metric="q", start_date="1981-01-01", end_date="2024-12-31")),
                         generated_at=GEN)
        r = rows(f, "cells.csv")[0]
        self.assertEqual(len(json.loads(r["footprint"])), 4)
        self.assertNotIn(" ", r["footprint"])
        self.assertIn(r["significant"], ("true", "false", ""))

    def test_decimal_point_and_utf8(self):
        raw = build_export(m.get_series(hq()), generated_at=GEN)["series.csv"]
        raw.decode("utf-8")
        self.assertNotIn(b"\r", raw)
        self.assertRegex(rows({"s": raw}, "s")[0]["value"], r"^-?\d+\.\d+$")


class JsonAndCardTests(unittest.TestCase):
    def test_json_is_strict(self):
        for resp in (m.get_series(hq()), m.get_series(hq("MOCK_ERROR")), m.get_capabilities(hq())):
            for name, data in build_export(resp, generated_at=GEN).items():
                if name.endswith(".json"):
                    json.loads(data, parse_constant=lambda c: self.fail(f"{name}: {c}"))

    def test_hypothesis_and_time_do_not_change_analysis(self):
        resp = m.get_series(hq())
        a = build_evidence_card_ext(resp, "mas calor", "2026-01-01T00:00:00Z")
        b = build_evidence_card_ext(resp, "", "2027-01-01T00:00:00Z")
        for k in ("result_id", "results", "summary", "data_sha256", "query", "availability"):
            self.assertEqual(a[k], b[k], k)
        self.assertNotEqual((a["hypothesis"], a["generated_at"]), (b["hypothesis"], b["generated_at"]))

    def test_card_keeps_v2_fields_and_extensions(self):
        card = build_evidence_card_ext(m.get_series(hq()), generated_at=GEN)
        for k in ("schema_version", "result_id", "preset_id", "hypothesis", "query", "synthetic", "summary",
                  "results", "warnings", "source_ids", "data_sha256", "mask_version", "analysis_version",
                  "generated_at", "product", "availability", "source_mode", "query_effective",
                  "geographic_context", "data_coverage", "forecast_metadata", "distribution_metadata",
                  "service_coverage_metadata"):
            self.assertIn(k, card)

    def test_synthetic_label_visible_and_never_presentable_as_real(self):
        f = build_export(m.get_series(hq()), generated_at=GEN)
        self.assertIn("sinteticos", f["ficha.md"].decode("utf-8"))
        card = json.loads(f["evidence.json"])
        self.assertIs(card["presentable_as_real"], False)
        self.assertIn("sinteticos", card["summary"])

    def test_unknown_provenance_blocks_real_claim(self):
        from src.contracts import to_jsonable
        d = to_jsonable(m.get_series(hq()))
        d["source_mode"], d["synthetic"] = "unknown", None
        card = build_evidence_card_ext(d, generated_at=GEN)
        self.assertFalse(card["presentable_as_real"])
        self.assertIn("no presentable como real", card["summary"])

    def test_summary_states_partial_stale_and_absence(self):
        self.assertIn("Cobertura parcial", build_evidence_card_ext(
            m.get_series(AnalysisQuery("historical", "T2M", zone_ids=("MOCK_PARTIAL",))))["summary"])
        self.assertIn("Vencido", build_evidence_card_ext(m.get_series(hq("MOCK_STALE")))["summary"])
        self.assertIn("Sin resultado", build_evidence_card_ext(m.get_series(hq("MOCK_NODATA")))["summary"])

    def test_event_summary_flags_missing_anomaly(self):
        q = AnalysisQuery("event", "PRECTOTCORR", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98",
                          baseline="1981-1990")
        self.assertIn("anomalia no disponible", build_evidence_card_ext(m.get_event_series(q))["summary"])


if __name__ == "__main__":
    unittest.main()
