# -*- encoding: utf-8 -*-
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

import os
import uuid
from collections import namedtuple

BatchFile = namedtuple("BatchFile", ["filename_dbrecord", "filename", "email", "model_name"])


class BatchFilesDB():

    ENTRIES = '/srv/data/entries'
    SEPARATOR = "\t"

    def create(self, filename, email, model_name):
        os.makedirs(self.ENTRIES, exist_ok=True)
        filename_dbrecord = os.path.join(self.ENTRIES, str(uuid.uuid4()))
        with open(filename_dbrecord, "w") as fh:
            fh.write(self.SEPARATOR.join([filename, email, model_name]))

        return filename_dbrecord

    def _read_record(self, filename_dbrecord):
        with open(filename_dbrecord, "r") as fh:
            return BatchFile(filename_dbrecord, *fh.readline().split(self.SEPARATOR)[:3])

    def select(self):
        os.makedirs(self.ENTRIES, exist_ok=True)
        return [self._read_record(os.path.join(self.ENTRIES, name)) for name in os.listdir(self.ENTRIES)]

    def delete(self, filename):
        os.remove(filename)
