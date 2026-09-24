#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
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

"""Shared command-line plumbing for model_to_po and model_to_txt."""

import logging
from optparse import OptionParser


def init_logging(logfile):
    logging.basicConfig(filename=logfile, filemode='w', format='%(message)s', level=logging.WARNING)


def base_parser(file_option, file_help):
    parser = OptionParser()
    parser.add_option('-m', '--model_name', default='eng-cat', dest='model_name',
                      help="Translation model name. For example 'eng-cat' or 'cat-eng'")
    parser.add_option('-f', file_option, dest='input_file', help=file_help)
    parser.add_option('-t', '--translated-file', dest='translated_file',
                      help='Name of the translated file')
    parser.add_option('-x', '--models', dest='models_path', default='',
                      help='Path the model directory')
    return parser
