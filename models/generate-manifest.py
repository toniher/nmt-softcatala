#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Jordi Mas i Hernandez <jmas@softcatala.org>
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

# Prints the list of available model zip filenames from the published index,
# in the format expected by models/models.list. Redirect the output to update
# the manifest when new models are published:
#
#   python3 models/generate-manifest.py > models/models.list

from bs4 import BeautifulSoup
import requests
import os
from urllib.parse import urlparse


URL = 'https://www.softcatala.org/pub/softcatala/opennmt/models/2022-11-22/'
EXT = 'zip'

def get_list_of_models(url, ext=''):
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]

def get_filename(url):
    a = urlparse(url)
    return os.path.basename(a.path)


def main():
    models = get_list_of_models(URL, EXT)
    for url in models:
        print(get_filename(url))

if __name__ == "__main__":
    main()
