"""Motor de predicciones regionales (`hefesto_forecast`): reproduce los números publicados y respeta sus límites."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from hefesto_forecast.engine import DATA, ForecastEngine, NeedsRevalidation, validate_series

EXPECTED = Path(__file__).parent / "fixtures" / "forecast" / "expected.json"


class EngineTests(unittest.TestCase):
    def test_reproduces_all_published_numbers(self):
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        engine = ForecastEngine()
        for region in ["CR", "CR_PN", "CR_CAR"]:
            for variable in ["T2M", "RH2M", "PRECTOTCORR", "UV"]:
                result = engine.forecast(region, variable, "2026-12", 6)
                json.dumps(result, allow_nan=False)
                for row in result["rows"]:
                    e = next(x for x in expected if x["region"] == region and x["variable"] == variable and x["target_month"] == row["target_month"])
                    self.assertEqual(row["status"], e["status"])
                    for field in ["estimate", "lower90", "upper90"]:
                        if e[field] is None:
                            self.assertIsNone(row[field])
                        else:
                            self.assertAlmostEqual(row[field], e[field], places=6)
                    for field in ["mean", "p10", "p90"]:
                        self.assertAlmostEqual(row["reference"][field], e["reference"][field], places=6)

    def test_does_not_extend_old_forecasts(self):
        result = ForecastEngine().forecast("CR", "T2M", "2028-01", 6)
        self.assertTrue(all(x["estimate"] is None for x in result["rows"]))

    def test_no_isolated_long_horizon(self):
        result = ForecastEngine().forecast("CR_PN", "T2M", "2026-12", 6)
        self.assertIsNone(result["rows"][3]["estimate"])  # marzo: no saltar febrero fallido

    def test_only_temperature_is_forecast(self):
        engine = ForecastEngine()
        for variable in ["RH2M", "PRECTOTCORR", "UV"]:
            rows = engine.forecast("CR", variable, "2026-12", 6)["rows"]
            self.assertTrue(all(r["estimate"] is None and r["status"] == "seasonal_reference" for r in rows), variable)

    def test_changed_data_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(DATA, tmp, dirs_exist_ok=True)
            path = Path(tmp) / "monthly_regional.csv"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(NeedsRevalidation):
                ForecastEngine(tmp)

    def test_bad_inputs(self):
        engine = ForecastEngine()
        for region, var, start, months in [("101", "T2M", "2026-12", 6), ("CR", "UV", "2026-13", 6), ("CR", "T2M", "2024-01", 6), ("CR", "T2M", "2026-12", 7)]:
            with self.assertRaises(ValueError):
                engine.forecast(region, var, start, months)

    def test_missing_duplicate_and_nan_months(self):
        s = pd.Series(np.arange(121.0), index=pd.date_range("2001-01-01", periods=121, freq="MS"))
        for bad in [s.drop(s.index[10]), pd.concat([s, s.iloc[-1:]]), s.mask(s == 4)]:
            with self.assertRaises(ValueError):
                validate_series(bad)


if __name__ == "__main__":
    unittest.main()


class FingerprintTests(unittest.TestCase):
    def test_line_endings_do_not_change_the_data_fingerprint(self):
        """Git en Windows entrega los CSV con CRLF: el mismo contenido debe dar la misma huella (y un cambio real, otra)."""
        import tempfile
        from pathlib import Path
        from hefesto_forecast.engine import file_digest
        crlf, lf = bytes([13, 10]), bytes([10])
        with tempfile.TemporaryDirectory() as tmp:
            a, b, c = (Path(tmp) / name for name in ("a.csv", "b.csv", "c.csv"))
            a.write_bytes(b"x,y" + crlf + b"1,2" + crlf)
            b.write_bytes(b"x,y" + lf + b"1,2" + lf)
            c.write_bytes(b"x,y" + lf + b"1,3" + lf)
            self.assertEqual(file_digest(a), file_digest(b))
            self.assertNotEqual(file_digest(a), file_digest(c))
