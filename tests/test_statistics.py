"""Pruebas de la Entrega 2 (EMANUEL): comparacion historica y OLS descriptiva.

Usa los fixtures sinteticos de EMANUEL-02 (tests/fixtures/stats/*.json) como
referencia numerica independiente para las rectas conocidas y la serie
constante (ver tests/fixtures/stats/README.md).
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from src import statistics

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "stats"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def annual_rows(
    years: list[int],
    values: list[float | None],
    *,
    variable: str = "T2M",
    region_id: str = "CR_PN",
) -> list[dict[str, Any]]:
    assert len(years) == len(values)
    return [
        {"region_id": region_id, "variable": variable, "year": y, "value": v}
        for y, v in zip(years, values)
    ]


class DefaultWindowsTest(unittest.TestCase):
    def test_full_coverage_matches_plan_example(self):
        window_a, window_b = statistics.default_windows(1981, 2024)
        self.assertEqual(window_a, (1981, 2002))
        self.assertEqual(window_b, (2003, 2024))

    def test_odd_coverage_excludes_oldest_year(self):
        # 1981-2023: 43 anios (impar) -> 1981 se excluye del valor por defecto.
        window_a, window_b = statistics.default_windows(1981, 2023)
        self.assertEqual(window_a, (1982, 2002))
        self.assertEqual(window_b, (2003, 2023))
        for start, end in (window_a, window_b):
            self.assertEqual(end - start + 1, 21)

    def test_windows_are_equal_length_and_non_overlapping(self):
        window_a, window_b = statistics.default_windows(2000, 2019)
        len_a = window_a[1] - window_a[0] + 1
        len_b = window_b[1] - window_b[0] + 1
        self.assertEqual(len_a, len_b)
        self.assertEqual(window_a[1] + 1, window_b[0])

    def test_insufficient_span_raises(self):
        with self.assertRaises(ValueError):
            statistics.default_windows(2000, 2000)

    def test_start_after_end_raises(self):
        with self.assertRaises(ValueError):
            statistics.default_windows(2010, 2000)


class ComputeWindowStatsGapsTest(unittest.TestCase):
    def test_requested_bounds_are_preserved_despite_gap(self):
        years = list(range(2000, 2012))  # 12 anios solicitados
        values = [20.0 + 0.1 * i for i in range(12)]
        values[5] = None  # hueco en medio de la ventana
        rows = annual_rows(years, values)
        stats = statistics.compute_window_stats(rows, 2000, 2011, variable="T2M")
        self.assertEqual(stats.start_year, 2000)
        self.assertEqual(stats.end_year, 2011)
        self.assertEqual(stats.n_years, 11)
        self.assertNotIn(years[5], stats.years_used)
        self.assertIn("gaps_in_window", stats.warnings)
        # con 11 anios validos si hay pendiente descriptiva
        self.assertEqual(stats.level, "descriptive")
        self.assertEqual(stats.status, "ok")
        self.assertIsNotNone(stats.slope_per_decade)

    def test_no_data_in_window_reports_absent_without_raising(self):
        rows = annual_rows([2000, 2001], [None, None])
        stats = statistics.compute_window_stats(rows, 2000, 2010, variable="T2M")
        self.assertEqual(stats.n_years, 0)
        self.assertIsNone(stats.mean)
        self.assertIsNone(stats.slope_per_decade)
        self.assertEqual(stats.status, "insufficient_data")
        self.assertIn("no_data", stats.warnings)


class ComputeWindowStatsMultiRegionAndDuplicatesTest(unittest.TestCase):
    """Sin region_id explicito, una ventana con mas de una region es ambigua;
    una serie con anios duplicados tampoco se promedia en silencio."""

    def test_two_regions_five_years_each_is_not_ten_valid_years(self):
        years_pn = [2000, 2001, 2002, 2003, 2004]
        years_car = [2000, 2001, 2002, 2003, 2004]
        rows = annual_rows(years_pn, [20.0, 20.1, 20.2, 20.3, 20.4], region_id="CR_PN")
        rows += annual_rows(years_car, [25.0, 25.1, 25.2, 25.3, 25.4], region_id="CR_CAR")
        with self.assertRaises(ValueError):
            statistics.compute_window_stats(rows, 2000, 2004, variable="T2M")

    def test_two_regions_resolved_once_region_id_given(self):
        years = [2000, 2001, 2002, 2003, 2004]
        rows = annual_rows(years, [20.0, 20.1, 20.2, 20.3, 20.4], region_id="CR_PN")
        rows += annual_rows(years, [25.0, 25.1, 25.2, 25.3, 25.4], region_id="CR_CAR")
        stats = statistics.compute_window_stats(rows, 2000, 2004, variable="T2M", region_id="CR_PN")
        self.assertEqual(stats.n_years, 5)

    def test_duplicate_year_in_single_region_series_raises(self):
        rows = annual_rows([2000, 2001, 2001, 2002], [10.0, 11.0, 99.0, 12.0])
        with self.assertRaises(ValueError):
            statistics.compute_window_stats(rows, 2000, 2002, variable="T2M")


class ComputeWindowStatsThresholdTest(unittest.TestCase):
    """Frontera de 10 anios validos (PLAN-HEFESTO seccion 3, 'OLS')."""

    def test_nine_years_is_insufficient_data(self):
        years = list(range(1990, 1999))  # 9 anios
        values = [20.0 + 0.1 * i for i in range(9)]
        rows = annual_rows(years, values)
        stats = statistics.compute_window_stats(rows, years[0], years[-1], variable="T2M")
        self.assertEqual(stats.n_years, 9)
        self.assertEqual(stats.level, "none")
        self.assertEqual(stats.status, "insufficient_data")
        self.assertIsNone(stats.slope_per_decade)
        self.assertIsNone(stats.total_change)
        self.assertIsNotNone(stats.mean)  # el promedio si se publica
        self.assertIn("short_record", stats.warnings)

    def test_ten_years_is_descriptive(self):
        years = list(range(1990, 2000))  # 10 anios
        values = [20.0 + 0.1 * i for i in range(10)]
        rows = annual_rows(years, values)
        stats = statistics.compute_window_stats(rows, years[0], years[-1], variable="T2M")
        self.assertEqual(stats.n_years, 10)
        self.assertEqual(stats.level, "descriptive")
        self.assertEqual(stats.status, "ok")
        self.assertAlmostEqual(stats.slope_per_decade, 1.0)  # 0.1/anio * 10
        self.assertAlmostEqual(stats.total_change, 0.1 * (years[-1] - years[0]))


class ComputeWindowStatsKnownLinesTest(unittest.TestCase):
    """Cruza directamente con los fixtures de rectas exactas y serie constante."""

    def _check_fixture(self, name: str, variable: str):
        fx = load_fixture(name)
        years = fx["input"]["years"]
        values = fx["input"]["annual_values"]
        rows = annual_rows(years, values, variable=variable)
        stats = statistics.compute_window_stats(rows, years[0], years[-1], variable=variable)
        expected = fx["expected"]
        self.assertEqual(stats.n_years, expected["years_used"] if "years_used" in expected else len(years))
        self.assertAlmostEqual(stats.slope_per_decade, expected["slope_per_decade"], places=6)
        self.assertAlmostEqual(stats.total_change, expected["adjusted_change"], places=6)
        self.assertEqual(stats.first_used_year, years[0])
        self.assertEqual(stats.last_used_year, years[-1])

    def test_linear_trend_increase_matches_fixture(self):
        self._check_fixture("linear_trend_increase", "T2M")

    def test_linear_trend_decrease_matches_fixture(self):
        self._check_fixture("linear_trend_decrease", "T2M")

    def test_constant_series_has_zero_slope_and_change(self):
        fx = load_fixture("constant_precip")
        years = fx["input"]["years"]
        values = fx["input"]["annual_values"]
        rows = annual_rows(years, values, variable="PRECTOTCORR")
        stats = statistics.compute_window_stats(rows, years[0], years[-1], variable="PRECTOTCORR")
        self.assertAlmostEqual(stats.slope_per_decade, 0.0)
        self.assertAlmostEqual(stats.total_change, 0.0)
        self.assertAlmostEqual(stats.mean, 730.0)


class CompareHistoricalWindowsTest(unittest.TestCase):
    def test_default_windows_full_coverage(self):
        years = list(range(1981, 2025))
        values = [20.0 + 0.05 * i for i in range(len(years))]
        rows = annual_rows(years, values)
        comparison = statistics.compare_historical_windows(rows, variable="T2M")
        self.assertTrue(comparison.uses_default_windows)
        self.assertEqual((comparison.window_a.start_year, comparison.window_a.end_year), (1981, 2002))
        self.assertEqual((comparison.window_b.start_year, comparison.window_b.end_year), (2003, 2024))
        self.assertIsNotNone(comparison.mean_diff_b_minus_a)
        self.assertGreater(comparison.mean_diff_b_minus_a, 0.0)

    def test_explicit_windows_within_coverage(self):
        years = list(range(1981, 2025))
        values = [20.0 + 0.05 * i for i in range(len(years))]
        rows = annual_rows(years, values)
        comparison = statistics.compare_historical_windows(
            rows, variable="T2M", window_a=(1985, 2000), window_b=(2001, 2020)
        )
        self.assertFalse(comparison.uses_default_windows)
        self.assertEqual((comparison.window_a.start_year, comparison.window_a.end_year), (1985, 2000))
        self.assertEqual((comparison.window_b.start_year, comparison.window_b.end_year), (2001, 2020))

    def test_only_one_explicit_window_raises(self):
        rows = annual_rows(list(range(1981, 2025)), [20.0] * 44)
        with self.assertRaises(ValueError):
            statistics.compare_historical_windows(rows, variable="T2M", window_a=(1981, 2000))

    def test_explicit_window_outside_given_coverage_raises(self):
        # coverage_start/end_year acotan 2000-2004; una ventana 1981-1990 cae
        # fuera de esa cobertura aunque este dentro del contrato global.
        rows = annual_rows(list(range(1981, 2025)), [20.0] * 44)
        with self.assertRaises(ValueError):
            statistics.compare_historical_windows(
                rows,
                variable="T2M",
                window_a=(1981, 1990),
                window_b=(2000, 2004),
                coverage_start_year=2000,
                coverage_end_year=2004,
            )

    def test_sign_of_difference_positive_when_b_is_higher(self):
        # Ventana A plana en 10.0, ventana B plana en 20.0 con pendiente mayor.
        years_a = list(range(1981, 2003))  # 22 anios
        years_b = list(range(2003, 2025))  # 22 anios
        values_a = [10.0 + 0.01 * i for i in range(len(years_a))]
        values_b = [30.0 + 0.5 * i for i in range(len(years_b))]
        rows = annual_rows(years_a + years_b, values_a + values_b)
        comparison = statistics.compare_historical_windows(rows, variable="T2M")
        self.assertGreater(comparison.mean_diff_b_minus_a, 0.0)
        self.assertGreater(comparison.slope_diff_b_minus_a, 0.0)

    def test_sign_of_difference_negative_when_b_is_lower(self):
        years_a = list(range(1981, 2003))
        years_b = list(range(2003, 2025))
        values_a = [30.0 + 0.5 * i for i in range(len(years_a))]
        values_b = [10.0 + 0.01 * i for i in range(len(years_b))]
        rows = annual_rows(years_a + years_b, values_a + values_b)
        comparison = statistics.compare_historical_windows(rows, variable="T2M")
        self.assertLess(comparison.mean_diff_b_minus_a, 0.0)
        self.assertLess(comparison.slope_diff_b_minus_a, 0.0)

    def test_missing_estimate_in_one_window_makes_diff_none(self):
        # Ventana A con solo 5 anios validos (<10): sin pendiente -> slope_diff None.
        years_a = list(range(1981, 2003))
        years_b = list(range(2003, 2025))
        values_a = [None] * (len(years_a) - 5) + [10.0, 11.0, 12.0, 13.0, 14.0]
        values_b = [20.0 + 0.1 * i for i in range(len(years_b))]
        rows = annual_rows(years_a + years_b, values_a + values_b)
        comparison = statistics.compare_historical_windows(rows, variable="T2M")
        self.assertEqual(comparison.window_a.n_years, 5)
        self.assertIsNone(comparison.window_a.slope_per_decade)
        self.assertIsNotNone(comparison.window_a.mean)
        self.assertIsNone(comparison.slope_diff_b_minus_a)
        self.assertIsNotNone(comparison.mean_diff_b_minus_a)

    def test_invalid_variable_raises(self):
        rows = annual_rows(list(range(1981, 2025)), [20.0] * 44)
        with self.assertRaises(ValueError):
            statistics.compare_historical_windows(rows, variable="NOPE")

    def test_distinct_region_per_window_without_region_id_raises(self):
        # CR_PN solo aparece en los anios de la ventana A por defecto
        # (1981-2002) y CR_CAR solo en los de la ventana B (2003-2024). Cada
        # ventana por separado no es ambigua, pero comparar A contra B
        # compararia dos regiones distintas sin que se pidiera.
        rows_a = annual_rows(list(range(1981, 2003)), [20.0] * 22, region_id="CR_PN")
        rows_b = annual_rows(list(range(2003, 2025)), [25.0] * 22, region_id="CR_CAR")
        with self.assertRaises(ValueError):
            statistics.compare_historical_windows(rows_a + rows_b, variable="T2M")

    def test_region_id_filters_rows(self):
        years = list(range(1981, 2025))
        rows_pn = annual_rows(years, [20.0 + 0.05 * i for i in range(len(years))], region_id="CR_PN")
        rows_car = annual_rows(years, [15.0 + 0.5 * i for i in range(len(years))], region_id="CR_CAR")
        comparison = statistics.compare_historical_windows(
            rows_pn + rows_car, variable="T2M", region_id="CR_PN"
        )
        self.assertEqual(comparison.region_id, "CR_PN")
        # la pendiente debe salir de la serie CR_PN (mas plana), no de CR_CAR
        self.assertLess(comparison.window_a.slope_per_decade, 1.0)


class TStudentReferenceTest(unittest.TestCase):
    """Valores de referencia estandar de la t-Student (tablas usuales), para
    la funcion beta incompleta regularizada detras de HAC."""

    def test_critical_value_matches_standard_table(self):
        self.assertAlmostEqual(statistics._t_critical_value(0.95, 30), 2.042, places=2)
        self.assertAlmostEqual(statistics._t_critical_value(0.95, 1), 12.706, places=2)
        self.assertAlmostEqual(statistics._t_critical_value(0.95, 120), 1.980, places=2)

    def test_two_sided_p_at_critical_value_equals_alpha(self):
        df = 28
        t_crit = statistics._t_critical_value(0.95, df)
        self.assertAlmostEqual(statistics._t_two_sided_p(t_crit, df), 0.05, places=6)

    def test_two_sided_p_at_zero_is_one(self):
        self.assertEqual(statistics._t_two_sided_p(0.0, 30), 1.0)


class LongTermTrendThresholdTest(unittest.TestCase):
    """Frontera de 29/30 anios consecutivos para intentar inferencia HAC
    (PLAN-HEFESTO seccion 3, 'HAC')."""

    def test_29_years_is_descriptive_not_inferential(self):
        fx = load_fixture("ar1_seed42")
        years = fx["input"]["years"][:29]
        values = fx["input"]["annual_values"][:29]
        rows = annual_rows(years, values)
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="T2M")
        trend = result.trend
        self.assertEqual(trend.n_years, 29)
        self.assertEqual(trend.level, "descriptive")
        self.assertEqual(trend.status, "ok")
        self.assertIsNotNone(trend.slope_per_decade)
        self.assertIsNone(trend.se_hac)
        self.assertIsNone(trend.p_value)
        self.assertIsNone(trend.hac_lags)
        self.assertEqual(result.sensitivity, ())

    def test_30_consecutive_noisy_years_is_inferential(self):
        fx = load_fixture("ar1_seed42")
        years = fx["input"]["years"]
        values = fx["input"]["annual_values"]
        rows = annual_rows(years, values)
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="T2M")
        trend = result.trend
        self.assertEqual(trend.n_years, 30)
        self.assertEqual(trend.level, "inferential")
        self.assertEqual(trend.status, "ok")
        self.assertEqual(trend.hac_lags, 3)
        self.assertIsNotNone(trend.se_hac)
        self.assertGreater(trend.se_hac, 0.0)
        self.assertIsNotNone(trend.p_value)
        self.assertGreaterEqual(trend.p_value, 0.0)
        self.assertLessEqual(trend.p_value, 1.0)
        self.assertLess(trend.ci_low, trend.slope_per_decade)
        self.assertGreater(trend.ci_high, trend.slope_per_decade)
        self.assertEqual([s.lags for s in result.sensitivity], [1, 5])
        for sens in result.sensitivity:
            self.assertIsNotNone(sens.se_hac)
            self.assertGreater(sens.se_hac, 0.0)
            # la pendiente no depende de L: el punto medio del IC coincide
            midpoint = (sens.ci_low + sens.ci_high) / 2.0
            self.assertAlmostEqual(midpoint, trend.slope_per_decade, places=6)

    def test_gap_inside_window_blocks_inference_keeps_descriptive_magnitude(self):
        fx = load_fixture("ar1_seed42")
        years = list(fx["input"]["years"]) + [2020]
        values = list(fx["input"]["annual_values"]) + [21.0]
        values[15] = None  # hueco en medio de la ventana: 31 anios solicitados, 30 validos
        rows = annual_rows(years, values)
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="T2M")
        trend = result.trend
        self.assertEqual(trend.n_years, 30)
        self.assertEqual(trend.level, "descriptive")
        self.assertIsNotNone(trend.slope_per_decade)
        self.assertIsNone(trend.se_hac)
        self.assertIn("gaps_in_window", trend.warnings)
        self.assertEqual(result.sensitivity, ())

    def test_constant_series_30_years_is_descriptive_not_inferential(self):
        fx = load_fixture("constant_precip")
        years = fx["input"]["years"]
        values = fx["input"]["annual_values"]
        rows = annual_rows(years, values, variable="PRECTOTCORR")
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="PRECTOTCORR")
        trend = result.trend
        self.assertEqual(trend.n_years, 30)
        self.assertEqual(trend.level, "descriptive")
        self.assertAlmostEqual(trend.slope_per_decade, 0.0)
        self.assertIsNone(trend.se_hac)
        self.assertIsNone(trend.p_value)
        self.assertIn("degenerate_fit", trend.warnings)

    def test_exact_line_30_years_is_descriptive_not_inferential(self):
        fx = load_fixture("linear_trend_increase")
        years = fx["input"]["years"]
        values = fx["input"]["annual_values"]
        rows = annual_rows(years, values, variable="T2M")
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="T2M")
        trend = result.trend
        self.assertEqual(trend.level, "descriptive")
        self.assertAlmostEqual(trend.slope_per_decade, fx["expected"]["slope_per_decade"], places=6)
        self.assertIsNone(trend.se_hac)
        self.assertIn("degenerate_fit", trend.warnings)

    def test_nine_years_is_insufficient_data(self):
        years = list(range(1990, 1999))
        values = [20.0 + 0.1 * i for i in range(9)]
        rows = annual_rows(years, values)
        result = statistics.compute_long_term_trend(rows, years[0], years[-1], variable="T2M")
        self.assertEqual(result.trend.level, "none")
        self.assertEqual(result.trend.status, "insufficient_data")
        self.assertEqual(result.sensitivity, ())


class FdrByTest(unittest.TestCase):
    def test_matches_by_correction_fixture(self):
        fx = load_fixture("by_correction")
        pvals = [e["p"] for e in fx["input"]["entries"]]
        q = statistics.fdr_by(pvals)
        expected = fx["expected"]["q_in_original_order"]
        for got, exp in zip(q, expected):
            self.assertAlmostEqual(got, exp, places=9)

    def test_empty_input_returns_empty(self):
        self.assertEqual(statistics.fdr_by([]), [])


def _ar1_values(fixture: dict, *, base: float, slope: float, scale: float) -> list[float]:
    errors = fixture["input"]["errors"]
    return [base + slope * t + scale * e for t, e in enumerate(errors)]


class RegionalFamilyTest(unittest.TestCase):
    """BY regional sobre las 4 combinaciones variable x region de una ventana
    (PLAN-HEFESTO seccion 3, 'BY')."""

    def setUp(self):
        self.ar1 = load_fixture("ar1_seed42")
        self.years = self.ar1["input"]["years"]

    def _rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rows += annual_rows(self.years, self.ar1["input"]["annual_values"], variable="T2M", region_id="CR_PN")
        rows += annual_rows(
            self.years,
            _ar1_values(self.ar1, base=25.0, slope=0.01, scale=3.0),
            variable="T2M",
            region_id="CR_CAR",
        )
        # PRECTOTCORR:CR_PN constante -> ajuste degenerado, p_value ausente.
        rows += annual_rows(self.years, [700.0] * len(self.years), variable="PRECTOTCORR", region_id="CR_PN")
        rows += annual_rows(
            self.years,
            _ar1_values(self.ar1, base=1500.0, slope=-2.0, scale=50.0),
            variable="PRECTOTCORR",
            region_id="CR_CAR",
        )
        return rows

    def test_four_planned_tests_one_degenerate_excluded_from_valid(self):
        family = statistics.compute_regional_family(self._rows(), self.years[0], self.years[-1])
        self.assertEqual(family.planned_tests, 4)
        self.assertEqual(len(family.results), 4)
        self.assertEqual(family.valid_tests, 3)
        degenerate = next(t for t in family.results if t.variable == "PRECTOTCORR" and t.region_id == "CR_PN")
        self.assertIsNone(degenerate.p_value)
        self.assertIsNone(degenerate.p_adjusted)
        self.assertIsNone(degenerate.significant)
        self.assertIsNone(degenerate.family_id)

    def test_p_adjusted_matches_independent_fdr_by_recomputation(self):
        family = statistics.compute_regional_family(self._rows(), self.years[0], self.years[-1])
        valid = [t for t in family.results if t.p_value is not None]
        expected_q = statistics.fdr_by([t.p_value for t in valid])
        for trend, q in zip(valid, expected_q):
            self.assertAlmostEqual(trend.p_adjusted, q, places=12)
            self.assertEqual(trend.family_id, family.family_id)
            self.assertEqual(trend.significant, q < family.alpha)

    def test_filter_family_preserves_original_adjustment(self):
        family = statistics.compute_regional_family(self._rows(), self.years[0], self.years[-1])
        filtered = statistics.filter_family(family, region_id="CR_PN")
        self.assertEqual(len(filtered), 2)
        full_by_key = {(t.variable, t.region_id): t for t in family.results}
        for t in filtered:
            self.assertEqual(t.p_adjusted, full_by_key[(t.variable, t.region_id)].p_adjusted)

        # Si se recalculara BY solo sobre el subconjunto filtrado en vez de
        # conservar el ajuste de la familia completa, el resultado cambiaria:
        # aqui T2M:CR_PN es la unica fila filtrada con p_value.
        t2m_pn = next(t for t in filtered if t.variable == "T2M")
        recomputed_alone = statistics.fdr_by([t2m_pn.p_value])[0]
        self.assertGreater(abs(t2m_pn.p_adjusted - recomputed_alone), 1e-6)

    def test_filter_by_variable(self):
        family = statistics.compute_regional_family(self._rows(), self.years[0], self.years[-1])
        filtered = statistics.filter_family(family, variable="PRECTOTCORR")
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(t.variable == "PRECTOTCORR" for t in filtered))


if __name__ == "__main__":
    unittest.main()
