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

import logging
import os
import uuid
from collections import namedtuple

BatchFile = namedtuple("BatchFile", ["filename_dbrecord", "filename", "email", "model_name"])


class BatchFilesDB():

    ENTRIES = '/srv/data/entries'
    SEPARATOR = "\t"
    TMP_SUFFIX = ".tmp"

    def create(self, filename, email, model_name):
        os.makedirs(self.ENTRIES, exist_ok=True)
        filename_dbrecord = os.path.join(self.ENTRIES, str(uuid.uuid4()))
        # Write then rename so select() never sees a half-written record.
        with open(filename_dbrecord + self.TMP_SUFFIX, "w") as fh:
            fh.write(self.SEPARATOR.join([filename, email, model_name]))
        os.rename(filename_dbrecord + self.TMP_SUFFIX, filename_dbrecord)

        return filename_dbrecord

    def _read_record(self, filename_dbrecord):
        with open(filename_dbrecord, "r") as fh:
            fields = fh.readline().split(self.SEPARATOR)
        return BatchFile(filename_dbrecord, *fields) if len(fields) == 3 else None

    def select(self):
        os.makedirs(self.ENTRIES, exist_ok=True)
        records = []
        for name in os.listdir(self.ENTRIES):
            if name.endswith(self.TMP_SUFFIX):
                continue
            path = os.path.join(self.ENTRIES, name)
            record = self._read_record(path)
            if record:
                records.append(record)
            else:
                logging.error(f"Dropping malformed batch record {path}")
                self.delete(path)
        return records

    def delete(self, filename):
        os.remove(filename)
