"""Pruebas de control de calidad para datos y mascaras de Costa Rica (Hefesto v2).

Propietario: Samuel.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.contracts import REGION_IDS, VARIABLE_IDS

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
MOCK_DIR = ROOT / "data" / "mock"


class TestCostaRicaDataQC(unittest.TestCase):
    def test_processed_files_exist(self) -> None:
        for fname in ("grid_monthly.parquet", "masks.parquet", "provenance_base.json"):
            self.assertTrue((PROCESSED_DIR / fname).exists(), f"Falta {fname}")

    def test_grid_monthly_integrity(self) -> None:
        df = pd.read_parquet(PROCESSED_DIR / "grid_monthly.parquet")
        self.assertEqual(len(df), 10_560)
        self.assertFalse(df["synthetic"].any(), "Hay datos sinteticos en processed")

        key_cols = ["region_id", "variable", "lat", "lon", "time"]
        self.assertEqual(int(df.duplicated(subset=key_cols).sum()), 0)
        self.assertTrue(df["time"].dt.month.between(1, 12).all())

        self.assertEqual(set(df["region_id"].unique()), set(REGION_IDS))
        self.assertEqual(set(df["variable"].unique()), set(VARIABLE_IDS))

        t2m = df[df["variable"] == "T2M"]["value"]
        self.assertTrue(t2m.between(10.0, 40.0).all())

        pr = df[df["variable"] == "PRECTOTCORR"]["value"]
        self.assertTrue((pr >= 0.0).all())

    def test_masks_weights_and_cells(self) -> None:
        masks = pd.read_parquet(PROCESSED_DIR / "masks.parquet")
        for region_id in REGION_IDS:
            sub = masks[masks["region_id"] == region_id]
            self.assertGreaterEqual(len(sub), 2)
            self.assertTrue(np.isclose(float(sub["weight"].sum()), 1.0, atol=1e-6))

    def test_provenance_hashes_and_strict_json(self) -> None:
        raw_text = (PROCESSED_DIR / "provenance_base.json").read_text(encoding="utf-8")
        self.assertNotIn(": NaN", raw_text)
        self.assertNotIn(": Infinity", raw_text)
        prov = json.loads(raw_text)
        self.assertFalse(prov["synthetic"])
        self.assertIsNone(prov["provider_version"])

        for item in prov["raw_files"]:
            raw_path = ROOT / item["path"]
            self.assertTrue(raw_path.exists(), f"No existe archivo raw: {raw_path}")
            digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            self.assertEqual(digest, item["sha256"])

    def test_mock_isolated_and_flagged(self) -> None:
        mock_path = MOCK_DIR / "mock_grid.parquet"
        self.assertTrue(mock_path.exists())
        mock_df = pd.read_parquet(mock_path)
        self.assertTrue(mock_df["synthetic"].all())


if __name__ == "__main__":
    unittest.main()