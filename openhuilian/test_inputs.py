import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openhuilian.inputs import mask_rom, stock_up


class InputTests(unittest.TestCase):
    def test_explicit_path_and_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.touch()
            with patch.dict(os.environ, {"OPENHUILIAN_STOCK_UP": str(path),
                                         "OPENHUILIAN_MASK_ROM": str(path)}):
                self.assertEqual(stock_up(), path)
                self.assertEqual(mask_rom(), path)
                self.assertEqual(stock_up(path), path)
                self.assertEqual(mask_rom(path), path)

    def test_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            for locate, variable in [(stock_up, "OPENHUILIAN_STOCK_UP"),
                                     (mask_rom, "OPENHUILIAN_MASK_ROM")]:
                with self.subTest(variable=variable), self.assertRaisesRegex(SystemExit, variable):
                    locate()

    def test_empty_configuration(self):
        with patch.dict(os.environ, {"OPENHUILIAN_STOCK_UP": "", "OPENHUILIAN_MASK_ROM": ""}):
            for locate in (stock_up, mask_rom):
                with self.assertRaisesRegex(SystemExit, "Supply an input path"):
                    locate()

    def test_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as directory:
            for locate in (stock_up, mask_rom):
                with self.assertRaisesRegex(SystemExit, "input file not found"):
                    locate(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
