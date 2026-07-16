# -*- coding: utf-8 -*-
#
# Copyright (c) 2026 Softcatalà
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

import unittest
from engineselector import select_model

DEFAULT = "softcatala"


class SelectModelTest(unittest.TestCase):

    def _engines(self):
        return {
            "softcatala": {"eng-cat": "sc-eng-cat", "deu-cat": "sc-deu-cat"},
            "aina": {"eng-cat": "aina-eng-cat"},
        }

    def test_default_engine_when_none_requested(self):
        model = select_model(self._engines(), DEFAULT, "eng-cat", None)
        self.assertEqual(model, "sc-eng-cat")

    def test_unknown_engine_uses_default(self):
        model = select_model(self._engines(), DEFAULT, "eng-cat", "does-not-exist")
        self.assertEqual(model, "sc-eng-cat")

    def test_aina_hit(self):
        model = select_model(self._engines(), DEFAULT, "eng-cat", "aina")
        self.assertEqual(model, "aina-eng-cat")

    def test_aina_miss_falls_back_to_softcatala(self):
        model = select_model(self._engines(), DEFAULT, "deu-cat", "aina")
        self.assertEqual(model, "sc-deu-cat")

    def test_pair_absent_everywhere_returns_none(self):
        model = select_model(self._engines(), DEFAULT, "xxx-yyy", "aina")
        self.assertIsNone(model)


if __name__ == "__main__":
    unittest.main()
