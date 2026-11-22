import os
import tempfile
import unittest
from nmt_sc.model_to_txt import read_lines


class TestReadLines(unittest.TestCase):

    def _read(self, data):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
        try:
            return read_lines(f.name)
        finally:
            os.remove(f.name)

    def test_utf8(self):
        self.assertEqual(["Bon dia.", "Què tal?"], self._read("Bon dia.\nQuè tal?\n".encode("utf-8")))

    def test_utf8_bom_is_stripped(self):
        self.assertEqual(["Què tal?"], self._read("﻿Què tal?".encode("utf-8")))

    def test_windows_1252_keeps_accents(self):
        self.assertEqual(["Què tal, l·lusió?"], self._read("Què tal, l·lusió?\r\n".encode("cp1252")))

    def test_line_endings_and_blank_lines(self):
        self.assertEqual(["a", "", "b", "c"], self._read(b"a\r\n\r\nb\rc"))

    def test_empty_file(self):
        self.assertEqual([], self._read(b""))


if __name__ == '__main__':
    unittest.main()
