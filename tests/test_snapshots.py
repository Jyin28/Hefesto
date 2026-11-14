import copy
import json
import tempfile
import unittest
from datetime import date
from unittest import mock

from src import service_mock_f2 as m
from src import snapshots as sn
from src.contracts_ext import PRODUCTS, AnalysisQuery


def hq(zone="CR_PN", **kw):
    return AnalysisQuery("historical", "T2M", zone_ids=(zone,), **kw)


QUERIES = {
    "historical": (hq(), m.get_series),
    "event": (AnalysisQuery("event", "PRECTOTCORR", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98"),
              m.get_event_series),
    "forecast": (AnalysisQuery("forecast", "T2M", zone_ids=("CR_PN",), start_date="2025-01-01",
                               end_date="2025-06-30"), m.get_local_forecast),
    "water_distribution": (AnalysisQuery("water_distribution", None, zone_ids=("CR_PN",),
                                         start_date="2024-01-01", end_date="2024-06-30"),
                           m.get_water_distribution),
    "service_coverage": (AnalysisQuery("service_coverage", None, zone_ids=("CR_PN",),
                                       start_date="2024-01-01", end_date="2024-06-30"),
                         m.get_service_coverage),
}


def store():
    return sn.SnapshotStore(m.input_manifest, m.normalize_query, m.refresh_freshness)


def key(q, man=None, fn=""):
    return sn.cache_key(q, man or m.input_manifest(q), fn, m.normalize_query)


class KeyTests(unittest.TestCase):
    def test_stable(self):
        for p, (q, fn) in QUERIES.items():
            self.assertEqual(key(q, fn=fn.__name__), key(q, fn=fn.__name__), p)

    def test_normalization_ignores_id_order_and_duplicates(self):
        a = AnalysisQuery("historical", "T2M", zone_ids=("CR_PN", "CR_CAR"))
        b = AnalysisQuery("historical", "T2M", zone_ids=("CR_CAR", "CR_PN", "CR_PN"))
        self.assertEqual(key(a), key(b))

    def test_event_defaults_are_filled(self):
        a = AnalysisQuery("event", "T2M", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98")
        b = AnalysisQuery("event", "T2M", zone_ids=("CR_PN",), event_id="EL_NINO_1997_98",
                          baseline="1981-2010", start_date="1997-06-01", end_date="1998-05-31")
        self.assertEqual(key(a), key(b))

    def test_function_is_part_of_identity(self):
        q = hq()
        self.assertNotEqual(key(q, fn="get_series"), key(q, fn="get_map"))

    def test_query_changes_change_key(self):
        base = key(hq())
        self.assertNotEqual(base, key(hq(end_date="2020-12-31")))
        self.assertNotEqual(base, key(hq("CR_CAR")))
        self.assertNotEqual(base, key(AnalysisQuery("historical", "PRECTOTCORR", zone_ids=("CR_PN",))))

    def test_mock_and_real_never_share_entries(self):
        q = hq()
        man = m.input_manifest(q)
        real = {**man, "source_mode": "real"}
        self.assertNotEqual(key(q, man), key(q, real))
        self.assertTrue(key(q, man).startswith("mock:"))
        self.assertTrue(key(q, real).startswith("real:"))

    def test_time_fields_are_not_identity(self):
        man = m.input_manifest(hq())
        self.assertNotIn("generated_at", json.dumps(man))
        self.assertNotIn("checked_at", json.dumps(man))


class InvalidationMatrixTests(unittest.TestCase):
    def test_every_change_flips_exactly_the_listed_products(self):
        for change, part in sn.INVALIDATION_MATRIX.items():
            affected = set(sn.affected_products(change))
            for prod, (q, fn) in QUERIES.items():
                with self.subTest(change=change, product=prod):
                    man = m.input_manifest(q)
                    changed = copy.deepcopy(man)
                    changed[part] = {"_changed": change}
                    flipped = key(q, changed, fn.__name__) != key(q, man, fn.__name__)
                    self.assertEqual(flipped, prod in affected)

    def test_matrix_covers_planned_changes(self):
        need = {"zone_version", "geometry", "mask", "grid", "family_data", "method", "baseline", "event_id",
                "model_config", "issued_at", "data_cutoff", "horizon", "water_dataset", "corrections",
                "crosswalk", "indicator_definition", "denominator", "code", "schema"}
        self.assertTrue(need <= set(sn.INVALIDATION_MATRIX))
        self.assertTrue(all(p in PRODUCTS for c in sn.INVALIDATION_MATRIX for p in sn.affected_products(c)))

    def test_forecast_model_change_leaves_history_alone(self):
        self.assertNotIn("historical", sn.affected_products("model_config"))
        self.assertIn("forecast", sn.affected_products("model_config"))
        self.assertNotIn("forecast", sn.affected_products("denominator"))

    def test_real_changes_in_the_adapter_flip_the_right_keys(self):
        wq, wfn = QUERIES["water_distribution"]
        hq0, hfn = QUERIES["historical"]
        w0, h0 = key(wq, fn=wfn.__name__), key(hq0, fn=hfn.__name__)
        with mock.patch.object(m, "WATER_DATASET", "mock-water-2"):
            self.assertNotEqual(w0, key(wq, fn=wfn.__name__))
            self.assertEqual(h0, key(hq0, fn=hfn.__name__))
        with mock.patch.object(m, "ZONE_VERSION", "mock-2"):
            self.assertNotEqual(h0, key(hq0, fn=hfn.__name__))
        sq, sfn = QUERIES["service_coverage"]
        s0 = key(sq, fn=sfn.__name__)
        with mock.patch.dict(m._TARGET_HOUSEHOLDS, {"SA_PN_01": (13000, "MOCK_PADRON_2025")}):
            self.assertNotEqual(s0, key(sq, fn=sfn.__name__))  # new denominator -> new indicator key
            self.assertEqual(w0, key(wq, fn=wfn.__name__))  # water records do not depend on it


class StoreTests(unittest.TestCase):
    def test_hit_and_miss(self):
        s = store()
        q = hq()
        r1, hit1 = s.get_or_compute(q, m.get_series)
        r2, hit2 = s.get_or_compute(q, m.get_series)
        self.assertEqual((hit1, hit2, s.hits, s.misses, len(s)), (False, True, 1, 1, 1))
        self.assertEqual(r1["result_id"], r2["result_id"])

    def test_error_and_unsupported_not_cached(self):
        s = store()
        for q in (hq("MOCK_ERROR"), hq(time_resolution="daily")):
            _, hit = s.get_or_compute(q, m.get_series)
            _, hit2 = s.get_or_compute(q, m.get_series)
            self.assertEqual((hit, hit2), (False, False))
        self.assertEqual((len(s), s.uncached), (0, 4))

    def test_unavailable_is_cached(self):
        s = store()
        s.get_or_compute(hq("MOCK_NODATA"), m.get_series)
        self.assertEqual(len(s), 1)

    def test_forecast_freshness_reevaluated_on_read(self):
        s = store()
        q, fn = QUERIES["forecast"]
        first, _ = s.get_or_compute(q, fn)
        self.assertEqual(first["availability"]["status"], "available")
        with mock.patch.object(m, "_today", return_value=date(2031, 1, 1)):
            late, hit = s.get_or_compute(q, fn)
        self.assertTrue(hit)
        self.assertEqual((late["availability"]["status"], late["availability"]["reason_code"]),
                         ("stale", "forecast_expired"))
        self.assertEqual(late["forecast_metadata"]["issued_at"], first["forecast_metadata"]["issued_at"])
        self.assertEqual(late["payload"], first["payload"])
        self.assertEqual(late["result_id"], first["result_id"])
        again, _ = s.get_or_compute(q, fn)  # stored snapshot was not mutated
        self.assertEqual(again["availability"]["status"], "available")

    def test_cached_snapshot_not_aliased(self):
        s = store()
        q = hq()
        r1, _ = s.get_or_compute(q, m.get_series)
        r1["payload"].clear()
        r2, _ = s.get_or_compute(q, m.get_series)
        self.assertTrue(r2["payload"])

    def test_save_load_roundtrip(self):
        s = store()
        for q, fn in QUERIES.values():
            s.get_or_compute(q, fn)
        with tempfile.TemporaryDirectory() as d:
            names = s.save(d)
            self.assertEqual(len(names), 5)
            s2 = store()
            self.assertEqual(s2.load(d), 5)
            self.assertEqual(s2.keys(), s.keys())
            for q, fn in QUERIES.values():
                a, _ = s.get_or_compute(q, fn)
                b, hit = s2.get_or_compute(q, fn)
                self.assertTrue(hit)
                self.assertEqual(a, b)
            for n in names:  # strict JSON on disk
                with open(f"{d}/{n}", encoding="utf-8") as fh:
                    json.loads(fh.read(), parse_constant=lambda c: self.fail(c))


if __name__ == "__main__":
    unittest.main()
