"""Capas del Copernicus CDS (ERA5-Land + ERA5 UV) para el mapa «Datos CDS». Sin red: todo con datos sintéticos."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
xr = pytest.importorskip("xarray")

from src import cds  # noqa: E402

CELLS = [
    {"lat": 10.0, "lon": -84.0, "land_fraction": 1.0},
    {"lat": 10.0, "lon": -84.1, "land_fraction": 0.5},
    {"lat": 10.1, "lon": -84.0, "land_fraction": 0.3},  # celda costera: ERA5-Land no tiene dato (NaN)
]
for _cell in CELLS:
    _cell["id"] = f"ERA5L:{_cell['lat']:g}:{_cell['lon']:g}"
YEARS = cds.END_YEAR - cds.START_YEAR + 1
META = {"dataset": "x", "title": "Producto de prueba", "doi": "10.0/x", "url": "https://example.test",
        "sha256": "abc", "retrieved_at": "2026-01-01T00:00:00Z"}


def land_dataset(time_name="time"):
    times = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    lat, lon = np.array([10.2, 10.1, 10.0, 9.9]), np.array([-84.2, -84.1, -84.0, -83.9])
    shape = (len(times), len(lat), len(lon))
    t2m, tp = np.full(shape, 300.0), np.full(shape, 0.01)  # 26,85 °C y 10 mm/día
    t2m[:, 2, 1] = 290.0                                   # (10,0; -84,1) más fresca
    t2m[:, 1, 2] = np.nan; tp[:, 1, 2] = np.nan            # (10,1; -84,0) sin dato
    dims = (time_name, "latitude", "longitude")
    return xr.Dataset({"t2m": (dims, t2m), "d2m": (dims, t2m - 5.0), "tp": (dims, tp)},
                      coords={time_name: times, "latitude": lat, "longitude": lon})


def uv_dataset(time_name="time"):
    times = pd.date_range("1981-01-01", "2024-12-01", freq="MS")
    lat, lon = np.array([10.25, 10.0, 9.75]), np.array([-84.25, -84.0, -83.75])  # ERA5: 0,25° y latitud descendente
    index = (np.round((lat[:, None] - 9.75) / 0.25) * 3 + np.round((lon[None, :] + 84.25) / 0.25) + 1)
    uvb = np.broadcast_to(index * 172800.0, (len(times), 3, 3))  # 2 W/m² por cada unidad del índice
    return xr.Dataset({"uvb": ((time_name, "latitude", "longitude"), np.array(uvb))},
                      coords={time_name: times, "latitude": lat, "longitude": lon})


class ConversionsTest(unittest.TestCase):
    def test_units(self):
        self.assertAlmostEqual(cds.kelvin_to_celsius(273.15), 0.0)
        self.assertAlmostEqual(cds.metres_to_mm(0.003), 3.0)
        self.assertAlmostEqual(cds.joules_per_day_to_watts(86400.0), 1.0)

    def test_humidity(self):
        self.assertAlmostEqual(float(cds.relative_humidity(20.0, 20.0)), 100.0, places=6)
        self.assertAlmostEqual(float(cds.relative_humidity(30.0, 20.0)), 55.08, delta=0.3)
        self.assertEqual(float(cds.relative_humidity(20.0, 21.0)), 100.0)  # nunca pasa de 100 %


class BuildLayersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = cds.build_layers(land_dataset(), uv_dataset(), CELLS, META, META)

    def test_shape_matches_layer_contract(self):
        self.assertEqual(set(self.layers), {"T2M", "PRECTOTCORR", "RH2M", "UV"})
        for layer_id, layer in self.layers.items():
            self.assertEqual((layer["start"], layer["end"]), (1981, 2024), layer_id)
            self.assertEqual(len(layer["national"]), YEARS, layer_id)
            self.assertEqual(set(layer["cells"]), {c["id"] for c in CELLS}, layer_id)
            self.assertTrue(all(len(v) == YEARS for v in layer["cells"].values()), layer_id)

    def test_values(self):
        t2m = self.layers["T2M"]["cells"]
        self.assertAlmostEqual(t2m["ERA5L:10:-84"][0], 26.85, places=2)
        self.assertAlmostEqual(t2m["ERA5L:10:-84.1"][0], 16.85, places=2)
        # 10 mm/día durante el año (1981 no es bisiesto)
        self.assertAlmostEqual(self.layers["PRECTOTCORR"]["cells"]["ERA5L:10:-84"][0], 3650.0, places=1)
        rh = self.layers["RH2M"]["cells"]["ERA5L:10:-84"][0]
        self.assertAlmostEqual(rh, float(cds.relative_humidity(26.85, 21.85)), delta=0.05)

    def test_coastal_cell_takes_nearest_land_and_is_flagged(self):
        # (10,1; -84,0) llega vacía de ERA5-Land (mar): toma el punto de tierra más cercano (26,85 °C) y queda marcada.
        series = self.layers["T2M"]["cells"]["ERA5L:10.1:-84"]
        self.assertAlmostEqual(series[0], 26.85, places=2)
        self.assertEqual(self.layers["T2M"]["filled"], ["ERA5L:10.1:-84"])
        self.assertEqual(self.layers["T2M"]["provenance"]["filled_from_nearest_land"], 1)
        self.assertEqual(self.layers["UV"]["filled"], [])  # ERA5 (UV) no enmascara el mar

    def test_filled_cell_does_not_weigh_in_national(self):
        # Promedio ponderado por cos(lat) x fracción de tierra, solo con las dos celdas con dato propio (misma latitud).
        expected = (26.85 * 1.0 + 16.85 * 0.5) / 1.5
        self.assertAlmostEqual(self.layers["T2M"]["national"][0], expected, places=2)

    def test_cell_without_land_in_range_stays_none(self):
        # Con un radio menor que 0,1° no hay tierra a la que acudir: la celda sigue vacía y no se marca.
        picked, _, filled = cds._monthly_by_cell(land_dataset()["t2m"], CELLS, cds.GRID_TOLERANCE, fill_radius=0.05)
        self.assertEqual(filled, [])
        self.assertTrue(bool(np.isnan(picked.values[:, 2]).all()))

    def test_uv_takes_nearest_era5_point_and_is_flagged_resampled(self):
        uv = self.layers["UV"]
        self.assertTrue(uv["resampled"])
        self.assertTrue(uv["provenance"]["resampled"])
        self.assertFalse(self.layers["T2M"]["resampled"])  # la malla de 0,1° coincide con las celdas
        # (10,0; -84,0) es un punto exacto de ERA5: índice (1*3 + 1 + 1) = 5 -> 10 W/m²
        self.assertAlmostEqual(uv["cells"]["ERA5L:10:-84"][0], 10.0, places=3)
        # (10,1; -84,0) cae más cerca de la fila 10,0 que de la 10,25 -> mismo valor
        self.assertAlmostEqual(uv["cells"]["ERA5L:10.1:-84"][0], 10.0, places=3)

    def test_json_has_no_nan(self):
        json.dumps(self.layers, allow_nan=False)

    def test_uv_is_optional(self):
        layers = cds.build_layers(land_dataset(), None, CELLS, META)
        self.assertEqual(set(layers), {"T2M", "PRECTOTCORR", "RH2M"})

    def test_grid_outside_download_is_an_error(self):
        far = [{"lat": 12.0, "lon": -84.0, "land_fraction": 1.0, "id": "ERA5L:12:-84"}]
        with self.assertRaises(ValueError):
            cds.build_layers(land_dataset(), uv_dataset(), far, META, META)


class PlausibilityTest(unittest.TestCase):
    def test_unit_mistake_is_rejected(self):
        with self.assertRaises(ValueError):
            cds.check_plausible("PRECTOTCORR", {"a": [3.65]})      # m en vez de mm
        with self.assertRaises(ValueError):
            cds.check_plausible("T2M", {"a": [300.0]})             # K en vez de °C
        with self.assertRaises(ValueError):
            cds.check_plausible("UV", {"a": [None, None]})         # sin datos
        cds.check_plausible("T2M", {"a": [26.0, None]})


class FetchProductTest(unittest.TestCase):
    def test_cache_hit_never_calls_the_client(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder)
            (raw / cds.LAND["file"]).write_bytes(b"nc")
            (raw / cds.LAND["file"]).with_suffix(".meta.json").write_text(json.dumps(META), encoding="utf-8")
            factory = mock.Mock(side_effect=AssertionError("no debía descargar"))
            path, meta = cds.fetch_product(cds.LAND, raw, factory)
            self.assertEqual(path.name, cds.LAND["file"])
            self.assertEqual(meta["sha256"], "abc")
            factory.assert_not_called()

    def test_manual_file_without_meta_is_registered_not_downloaded(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder)
            (raw / cds.UV["file"]).write_bytes(b"nc")
            factory = mock.Mock(side_effect=AssertionError("no debía descargar"))
            path, meta = cds.fetch_product(cds.UV, raw, factory)
            self.assertTrue(meta["downloaded_manually"])
            self.assertEqual(len(meta["sha256"]), 64)
            self.assertTrue(path.with_suffix(".meta.json").is_file())
            factory.assert_not_called()

    def test_download_writes_file_and_provenance(self):
        class FakeClient:
            def retrieve(self, dataset, request, target):
                self.args = (dataset, request)
                Path(target).write_bytes(b"datos")

        with tempfile.TemporaryDirectory() as folder:
            client = FakeClient()
            path, meta = cds.fetch_product(cds.UV, Path(folder), lambda: client)
            self.assertEqual(path.read_bytes(), b"datos")
            self.assertFalse(path.with_suffix(".nc.part").exists())
            self.assertEqual(client.args[0], "reanalysis-era5-single-levels-monthly-means")
            self.assertEqual(client.args[1]["variable"], ["downward_uv_radiation_at_the_surface"])
            self.assertEqual(client.args[1]["year"][0], "1981")
            self.assertEqual(client.args[1]["year"][-1], "2024")
            self.assertEqual(len(meta["sha256"]), 64)
            self.assertTrue(path.with_suffix(".meta.json").is_file())

    def test_optional_product_never_downloads_even_with_a_key(self):
        factory = mock.Mock(side_effect=AssertionError("no debía descargar"))
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cds, "credentials_available", return_value=True):
            self.assertIsNone(cds.fetch_product(cds.UV, Path(folder), factory, optional=True))
            factory.assert_not_called()

    def test_required_product_without_file_or_key_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cds, "credentials_available", return_value=False):
            with self.assertRaises(cds.CdsCredentialsError):
                cds.fetch_product(cds.UV, Path(folder))

    def test_missing_credentials_has_a_clear_error(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cds, "credentials_available", return_value=False):
            with self.assertRaises(cds.CdsCredentialsError) as caught:
                cds.fetch_product(cds.LAND, Path(folder))
            self.assertIn(".cdsapirc", str(caught.exception))


class ExportTest(unittest.TestCase):
    def test_end_to_end_with_netcdf_files(self):
        pytest.importorskip("netCDF4")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "raw"
            raw.mkdir()
            # Los NetCDF nuevos del CDS usan `valid_time` en vez de `time`.
            land_dataset("valid_time").to_netcdf(raw / cds.LAND["file"])
            uv_dataset("valid_time").to_netcdf(raw / cds.UV["file"])
            for product in (cds.LAND, cds.UV):
                (raw / product["file"]).with_suffix(".meta.json").write_text(json.dumps(META), encoding="utf-8")
            cells_file = root / "cds_cells.json"
            cells_file.write_text(json.dumps([{k: c[k] for k in ("lat", "lon", "land_fraction")} for c in CELLS]), encoding="utf-8")
            target = root / "out" / "cds.json"
            cds.export_cds(raw, cells_file, target, client_factory=mock.Mock(side_effect=AssertionError))
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(set(payload["layers"]), {"T2M", "PRECTOTCORR", "RH2M", "UV"})
            self.assertIn("Copernicus", payload["attribution"])
            self.assertTrue(math.isclose(payload["layers"]["T2M"]["cells"]["ERA5L:10:-84"][0], 26.85, abs_tol=0.01))
            self.assertTrue(math.isclose(payload["layers"]["T2M"]["cells"]["ERA5L:10.1:-84"][0], 26.85, abs_tol=0.01))
            self.assertEqual(payload["layers"]["T2M"]["filled"], ["ERA5L:10.1:-84"])


    def test_end_to_end_without_uv_file(self):
        pytest.importorskip("netCDF4")
        # Con clave disponible y sin archivo UV: no se pide nada al CDS (el cliente fallaría si se llamara).
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cds, "credentials_available", return_value=True), \
                mock.patch.dict("sys.modules", {"cdsapi": None}):
            root = Path(folder)
            raw = root / "raw"
            raw.mkdir()
            land_dataset("valid_time").to_netcdf(raw / cds.LAND["file"])  # sin meta: se registra como descarga manual
            cells_file = root / "cds_cells.json"
            cells_file.write_text(json.dumps([{k: c[k] for k in ("lat", "lon", "land_fraction")} for c in CELLS]), encoding="utf-8")
            target = root / "cds.json"
            cds.export_cds(raw, cells_file, target)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(set(payload["layers"]), {"T2M", "PRECTOTCORR", "RH2M"})
            self.assertEqual(set(payload["products"]), {"land"})
            meta = json.loads((raw / cds.LAND["file"]).with_suffix(".meta.json").read_text(encoding="utf-8"))
            self.assertTrue(meta["downloaded_manually"])


if __name__ == "__main__":
    unittest.main()
