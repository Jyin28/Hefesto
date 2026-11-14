import dataclasses
import json
import math
import unittest

from src import contracts, service_mock as svc


class ContractsMockTest(unittest.TestCase):
    def test_imports_and_conventions(self):
        self.assertEqual(contracts.SCHEMA_VERSION, "2.0")
        self.assertEqual(contracts.REGION_IDS, ("CR_PN", "CR_CAR"))
        self.assertEqual(contracts.VARIABLE_IDS, ("T2M", "PRECTOTCORR"))
        self.assertEqual(svc.list_regions()[0].bbox, (-86.0, 9.75, -85.0, 11.25))

    def test_trend_has_all_required_fields(self):
        t = svc.get_trend("T2M", "CR_PN", 2010, 2024)
        names = {f.name for f in dataclasses.fields(contracts.TrendResult)}
        self.assertEqual(set(contracts.to_jsonable(t)), names)
        self.assertEqual(len(names), 23)
        self.assertEqual((t.level, t.status, t.slope_unit), ("descriptive", "ok", "degC/decade"))
        self.assertIn("synthetic", t.warnings)

    def test_levels_by_length(self):
        self.assertEqual(svc.get_trend("T2M", "CR_PN", 2000, 2008).level, "none")
        self.assertEqual(svc.get_trend("T2M", "CR_PN", 2000, 2009).level, "descriptive")
        self.assertEqual(svc.get_trend("T2M", "CR_PN", 1995, 2024).level, "inferential")

    def test_units_and_inclusive_period(self):
        rows = svc.get_annual_series("PRECTOTCORR", "CR_CAR", 1981, 1983)
        self.assertEqual([r["year"] for r in rows], [1981, 1982, 1983])
        self.assertTrue(all(r["unit"] == "mm/yr" and r["synthetic"] for r in rows))
        self.assertEqual(svc.get_trend("PRECTOTCORR", "CR_PN", 1981, 2024).slope_unit, "mm/yr/decade")

    def test_family_independent_of_view(self):
        a = svc.get_trend("T2M", "CR_PN", 1981, 2024)
        cmp_one = svc.get_comparison("T2M", 1981, 2024, regions=("CR_PN",))
        self.assertEqual(a.p_adjusted, cmp_one["results"][0]["p_adjusted"])
        self.assertEqual(cmp_one["family_metadata"][0]["planned_tests"], 4)
        self.assertEqual(a.family_id, "regions|T2M+PRECTOTCORR|CR_PN+CR_CAR|1981-2024|v2")

    def test_strict_json_no_nan(self):
        t = svc.get_trend("T2M", "CR_PN", 2010, 2024)
        d = json.loads(contracts.to_json(t))
        self.assertIsNone(d["p_value"])
        self.assertIsNone(d["significant"])
        bad = dataclasses.replace(t, slope_per_decade=math.nan, se_hac=math.inf)
        s = contracts.to_json(bad)
        self.assertNotIn("NaN", s)
        self.assertNotIn("Infinity", s)
        json.loads(s, parse_constant=lambda c: self.fail(f"non-strict constant {c}"))
        json.loads(contracts.to_json(svc.get_comparison("PRECTOTCORR", 1981, 2024)))

    def test_invalid_inputs_raise_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Variable invalida"):
            svc.get_trend("NOPE", "CR_PN", 1981, 2024)
        with self.assertRaisesRegex(ValueError, "Region invalida"):
            svc.get_trend("T2M", "XX", 1981, 2024)
        with self.assertRaisesRegex(ValueError, "Periodo invalido"):
            svc.get_trend("T2M", "CR_PN", 2024, 1981)
        with self.assertRaisesRegex(ValueError, "fuera de cobertura"):
            svc.get_trend("T2M", "CR_PN", 1970, 2024)

    def test_pending_functions_fail_loudly(self):
        with self.assertRaises(NotImplementedError):
            svc.get_event_view("T2M")  # P1

    def test_recommend_variable(self):
        heat = contracts.recommend_variable("heat")
        self.assertEqual(heat["recommendation"]["variable"], "T2M")
        self.assertEqual(heat["query"]["preset_id"], "CR_HEAT")
        rain = contracts.recommend_variable("rain")
        self.assertEqual((rain["recommendation"]["variable"], rain["query"]["preset_id"]),
                         ("PRECTOTCORR", "CR_RAIN"))
        with self.assertRaises(ValueError):
            contracts.recommend_variable("wind")

    def test_cell_trends_family_is_both_sectors(self):
        pn, meta = svc.get_cell_trends("T2M", "CR_PN", 1981, 2024)
        car, meta2 = svc.get_cell_trends("T2M", "CR_CAR", 1981, 2024)
        self.assertEqual(meta, meta2)
        self.assertEqual((meta["scope"], meta["planned_tests"], meta["method"]), ("cells", 10, "fdr_by"))
        self.assertTrue(all(c.q_value >= c.p_value for c in pn + car))
        self.assertTrue(all(c.significant == (c.q_value < 0.05) for c in pn))
        short, _ = svc.get_cell_trends("T2M", "CR_PN", 2010, 2024)
        self.assertTrue(all(c.significant is None and c.q_value is None for c in short))

    def test_edge_cases(self):
        fit = svc.fit_mock_trend
        rows = [(y, 20.0 + 0.03 * (y - 1981)) for y in range(1981, 2025)]
        gap = [r for r in rows if r[0] not in (2000, 2001)]
        t = fit(gap, "CR_PN", "T2M", 1981, 2024)
        self.assertEqual((t.level, t.p_value, t.ci_low, t.significant), ("descriptive", None, None, None))
        self.assertIn("temporal_gaps", t.warnings)
        self.assertEqual(t.n_years, 42)
        const = fit([(y, 5.0) for y in range(1981, 2025)], "CR_PN", "PRECTOTCORR", 1981, 2024)
        self.assertIn("degenerate_series", const.warnings)
        self.assertIsNone(const.p_value)
        self.assertEqual(const.slope_per_decade, 0.0)
        low = fit(rows, "CR_PN", "T2M", 1981, 2024, coverage_fraction=0.5)
        self.assertEqual((low.status, low.level), ("insufficient_data", "none"))
        for n, level in ((9, "none"), (15, "descriptive"), (30, "inferential"), (44, "inferential")):
            self.assertEqual(fit(rows[:n], "CR_PN", "T2M", 1981, 1980 + n).level, level)

    def test_by_without_discoveries(self):
        adj = svc._by_adjust([0.9, 0.8, 0.7, 0.95])
        self.assertTrue(all(q >= 0.7 and q <= 1.0 for q in adj))

    def test_evidence_card_matches_comparison_and_id_stable(self):
        q = contracts.QueryParams("PRECTOTCORR", ("CR_PN", "CR_CAR"), 1981, 2024, "CR_RAIN")
        a = svc.build_evidence_card(q, "Creo que llueve menos.")
        b = svc.build_evidence_card(q, "")
        cmp_ = svc.get_comparison("PRECTOTCORR", 1981, 2024)
        self.assertEqual(a["results"], cmp_["results"])
        self.assertEqual(a["family_metadata"], cmp_["family_metadata"])
        self.assertTrue(a["results"] and a["family_metadata"])
        self.assertEqual(a["result_id"], b["result_id"])  # hypothesis does not change identity
        other = svc.build_evidence_card(dataclasses.replace(q, end_year=2020))
        self.assertNotEqual(a["result_id"], other["result_id"])
        self.assertTrue(a["synthetic"])
        json.loads(contracts.to_json(a))
        json.loads(contracts.to_json(svc.build_provenance(q)))
        with self.assertRaises(ValueError):
            svc.build_evidence_card(dataclasses.replace(q, preset_id="X"))

    def test_mock_cells_match_real_mask(self):
        try:
            from src import regions
        except ImportError:
            self.skipTest("pandas/numpy not installed")
        for rid, cells in regions.VERIFIED_LAND_CELLS.items():
            self.assertEqual(tuple(cells), svc._MOCK_CELLS[rid])


if __name__ == "__main__":
    unittest.main()
