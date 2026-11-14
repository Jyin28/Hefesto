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
            svc.get_cell_trends("T2M", "CR_PN", 1981, 2024)


if __name__ == "__main__":
    unittest.main()
