"""Servicio real vs contrato v2/mock, estadística contra statsmodels, homogeneidad y ENOS 1997-98."""
import dataclasses
import inspect
import json
import unittest

import numpy as np
import statsmodels.api as sm

from src import service, service_mock
from src.contracts import QueryParams, TrendResult
from src.enso import episode_comparison
from src.export import build_export_bundle
from src.statistics import compute_long_term_trend, homogeneity_check
from src.web_data import ROOT, annual_rows, read_json

QUERY = QueryParams("T2M", ("CR_PN", "CR_CAR"), 1981, 2024, "CR_HEAT")


class ContractParityTest(unittest.TestCase):
    def test_same_signatures(self):
        for name in ("list_variables", "list_regions", "get_coverage", "get_annual_series", "get_trend",
                     "get_comparison", "get_cell_trends", "build_provenance", "build_evidence_card"):
            real = list(inspect.signature(getattr(service, name)).parameters)
            mock = list(inspect.signature(getattr(service_mock, name)).parameters)
            self.assertEqual(real, mock, name)

    def test_return_shapes_match_mock(self):
        r, m = service.build_evidence_card(QUERY, "h"), service_mock.build_evidence_card(QUERY, "h")
        self.assertTrue(set(m) <= set(r), set(m) - set(r))
        self.assertFalse(r["synthetic"])
        self.assertTrue(r["results"] and r["family_metadata"])
        self.assertEqual(set(r["results"][0]), set(m["results"][0]))
        self.assertEqual(set(service.get_comparison("T2M", 1981, 2024)["family_metadata"][0]),
                         set(service_mock.get_comparison("T2M", 1981, 2024)["family_metadata"][0]))
        rc = service.get_cell_trends("T2M", "CR_PN", 1981, 2024)
        rm = service_mock.get_cell_trends("T2M", "CR_PN", 1981, 2024)
        self.assertEqual(dataclasses.fields(rc[0][0]), dataclasses.fields(rm[0][0]))
        self.assertEqual(set(rc[1]), set(rm[1]))
        self.assertEqual({f.name for f in dataclasses.fields(TrendResult)}, set(r["results"][0]))

    def test_provenance_complete_and_validated(self):
        prov = service.build_provenance(QUERY)
        for key in ("schema_version", "query", "git_commit", "data_sha256", "hac", "correction_families",
                    "limitations", "synthetic", "raw_files", "mask_version"):
            self.assertIn(key, prov)
        self.assertFalse(prov["synthetic"])
        with self.assertRaises(ValueError):
            service.build_provenance(QueryParams("BAD", ("CR_PN", "CR_CAR"), 1981, 2024, "CR_HEAT"))
        with self.assertRaises(ValueError):
            service.build_evidence_card(QueryParams("T2M", ("CR_PN", "CR_CAR"), 1981, 2024, "NOPE"))

    def test_hypothesis_does_not_change_analysis_or_id(self):
        a, b = service.build_evidence_card(QUERY, ""), service.build_evidence_card(QUERY, "Creo que sube")
        self.assertEqual(a["result_id"], b["result_id"])
        self.assertEqual(a["results"], b["results"])

    def test_json_is_strict_and_family_is_full_even_when_viewing_one_region(self):
        card = service.build_evidence_card(QUERY)
        json.loads(build_export_bundle(card).evidence_json.decode())  # sin NaN/Infinity
        regional = card["family_metadata"][0]
        self.assertEqual((regional["planned_tests"], regional["scope"]), (4, "regions"))
        one = service.get_trend("PRECTOTCORR", "CR_PN", 1981, 2024)
        both = service.get_comparison("PRECTOTCORR", 1981, 2024)["results"]
        self.assertEqual(one.p_adjusted, both[0]["p_adjusted"])  # filtrar no cambia q
        cells, meta = service.get_cell_trends("T2M", "CR_PN", 1981, 2024)
        cells2, _ = service.get_cell_trends("T2M", "CR_CAR", 1981, 2024)
        self.assertEqual((meta["planned_tests"], len(cells) + len(cells2)), (10, 10))


class StatisticsAgainstStatsmodels(unittest.TestCase):
    def test_hac_matches_statsmodels_on_real_series(self):
        rows = annual_rows()
        for variable in ("T2M", "PRECTOTCORR"):
            for region in ("CR_PN", "CR_CAR"):
                series = [r for r in rows if r["region_id"] == region and r["variable"] == variable]
                years = np.array([r["year"] for r in series], float)
                values = np.array([r["value"] for r in series], float)
                fit = sm.OLS(values, sm.add_constant(years - years[0])).fit(
                    cov_type="HAC", cov_kwds={"maxlags": 3, "use_correction": True, "kernel": "bartlett"}, use_t=True)
                ours = compute_long_term_trend(rows, 1981, 2024, variable=variable, region_id=region).trend
                self.assertAlmostEqual(ours.slope_per_decade, fit.params[1] * 10, places=6)
                self.assertAlmostEqual(ours.se_hac, fit.bse[1] * 10, places=4)
                self.assertAlmostEqual(ours.p_value, fit.pvalues[1], places=6)
                lo, hi = np.asarray(fit.conf_int())[1] * 10
                self.assertAlmostEqual(ours.ci_low, lo, places=3)
                self.assertAlmostEqual(ours.ci_high, hi, places=3)

    def test_homogeneity_detects_a_synthetic_step_and_ignores_a_pure_trend(self):
        noise = lambda i: 0.1 * ((i * 7) % 5 - 2)
        step = [{"region_id": "CR_PN", "variable": "T2M", "year": 1981 + i,
                 "value": 20.0 + (5.0 if i >= 22 else 0.0) + noise(i)} for i in range(44)]
        h = homogeneity_check(step, 1981, 2024, variable="T2M", region_id="CR_PN")
        self.assertTrue(h["possible_inhomogeneity"])
        self.assertEqual(h["break_year"], 2003)
        trend = [{"region_id": "CR_PN", "variable": "T2M", "year": 1981 + i, "value": 20.0 + 0.05 * i + noise(i)}
                 for i in range(44)]
        self.assertFalse(homogeneity_check(trend, 1981, 2024, variable="T2M", region_id="CR_PN")["possible_inhomogeneity"])
        self.assertIsNone(homogeneity_check(step[:10], 1981, 1990, variable="T2M", region_id="CR_PN")["p_value"])


class EnsoEventTest(unittest.TestCase):
    def test_1997_98_event_is_default_and_descriptive(self):
        rows = service.get_event_view("T2M")
        self.assertEqual(len(rows), 24)  # 12 meses x 2 sectores
        self.assertEqual(rows[0]["time"], "1997-06-01")
        self.assertEqual(rows[11]["time"], "1998-05-01")
        self.assertTrue(all(r["baseline"] == "1981-2010" for r in rows))
        self.assertTrue(all(r["anomaly"] is not None for r in rows))
        self.assertIn("descriptivo", rows[0]["label"])

    def test_event_id_selects_episode(self):
        catalog = read_json(ROOT / "data" / "web" / "enso.json")
        monthly = [r for r in service.climate_package()[0]["regional_monthly"] if r["region_id"] == "CR_PN"]
        old = episode_comparison(monthly, "T2M", catalog, 1981, 2024, event_id="enos_2023_24")
        self.assertEqual(old["neutral_window"], ["2013-07", "2014-04"])
        self.assertEqual(episode_comparison(monthly, "T2M", catalog, 1981, 2024, event_id="x")["status"],
                         "episode_unavailable")


class CoverageFailureTest(unittest.TestCase):
    def test_low_spatial_coverage_gives_insufficient_data(self):
        rows = [{"region_id": "CR_PN", "variable": "T2M", "year": y, "value": None, "unit": "degC",
                 "months_valid": 12, "complete": False, "mean_monthly_coverage": 0.6,
                 "warnings": ("incomplete_year", "coverage_failure")} for y in range(1981, 2025)]
        t = compute_long_term_trend(rows, 1981, 2024, variable="T2M", region_id="CR_PN").trend
        self.assertEqual((t.status, t.level, t.p_value), ("insufficient_data", "none", None))
        self.assertIn("coverage_failure", t.warnings)
        self.assertEqual(t.coverage_fraction, 0.6)


if __name__ == "__main__":
    unittest.main()
