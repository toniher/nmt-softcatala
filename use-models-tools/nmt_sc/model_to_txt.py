#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Jordi Mas i Hernandez <jmas@softcatala.org>
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
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
import datetime
from concurrent.futures import ThreadPoolExecutor
from .ctranslate import CTranslate
from ._cli import init_logging, base_parser

def read_parameters():
    parser = base_parser('--txt-file', 'TXT File to translate')
    parser.add_option('-r', '--threads', type='int', dest='n_threads', default=0,
                      help='Number of threads in the client side (0 = inter threads)')
    (options, args) = parser.parse_args()
    if options.input_file is None:
        parser.error('TXT file not given')

    if options.translated_file is None:
        parser.error('Translate file not given')

    return options.model_name, options.input_file, options.translated_file, options.models_path, options.n_threads


def _get_words_per_second(start_time, words):
    time = datetime.datetime.now() - start_time
    total_seconds = time.total_seconds()
    words_second = words / total_seconds if total_seconds > 0 else 0
    return words_second


def main():

    print("Applies an OpenNMT model to translate a TXT file")
    print("For maximum performance when translating corpus using CPU, set")
    print("the environment variable CTRANSLATE_INTER_THREADS to your")
    print("number or processors and CTRANSLATE_INTRA_THREADS to 1")

    start_time = datetime.datetime.now()
    init_logging('model-to-txt.log')
    model_name, input_filename, translated_file, models_path, n_threads = read_parameters()
    openNMT = CTranslate(models_path, model_name)

    if n_threads == 0:
        n_threads = openNMT.inter_threads

    print(f'Client threads: {n_threads}')

    def translate(src):
        try:
            return openNMT.translate_parallel(src)
        except Exception as e:
            logging.error(str(e))
            logging.error("Processing: {0}".format(src))
            return None

    with open(input_filename, encoding='utf-8', mode='r', errors='ignore') as tf_en,\
         open(translated_file, encoding='utf-8', mode='w') as tf_ca,\
         ThreadPoolExecutor(n_threads) as executor:

        sources = [line.replace('\n', '') for line in tf_en]
        translated = 0
        errors = 0
        words = 0

        for src, tgt in zip(sources, executor.map(translate, sources)):
            translated += 1
            if tgt is None:
                errors += 1
                tgt = "Error"

            if translated % 500 == 0:
                per =  translated / len(sources) * 100
                words_second = _get_words_per_second(start_time, words)
                print(f" Sentences translated: {translated} ({per:.1f}%). Words/s {words_second:.1f}")

            tf_ca.write("{0}\n".format(tgt))
            logging.debug('Source: ' + str(src))
            logging.debug('Target: ' + str(tgt))
            words += len(src.split())

    time = datetime.datetime.now() - start_time
    words_second = _get_words_per_second(start_time, words)
    print("Sentences translated: {0}".format(translated))
    print("Sentences unable to translate {0} (NMT errors)".format(errors))
    print(f"Time used {time}. Words per second {words_second:.1f}")

if __name__ == "__main__":
    main()
