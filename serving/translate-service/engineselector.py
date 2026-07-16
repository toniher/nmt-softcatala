#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
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

"""Pure engine/model selection logic, kept free of Flask/CTranslate2 imports so
it can be unit-tested without the service's runtime dependencies."""


def select_model(engines, default_engine, languages, engine):
    """Return the translation model for a language pair within the requested
    engine, falling back to the default engine when the requested engine has no
    model for that pair.

    engines: dict of engine name -> {language pair: model}
    default_engine: engine used when none/unknown is requested and as fallback
    languages: ISO 639-3 pair, e.g. "eng-cat"
    engine: requested engine name (may be None/unknown)
    """
    engine = engine if engine in engines else default_engine
    model = engines[engine].get(languages)
    if model is None and engine != default_engine:
        model = engines[default_engine].get(languages)

    return model
