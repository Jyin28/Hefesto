"""Envuelve scripts/verify_data.py: los datos que usa el producto deben ser accesibles y consistentes."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerifyDataTest(unittest.TestCase):
    def test_verify_data_script_passes(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_data.py")], capture_output=True,
                             text=True, encoding="utf-8", timeout=300)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:] + out.stderr[-1000:])
        self.assertNotIn("FAIL", out.stdout)


if __name__ == "__main__":
    unittest.main()
