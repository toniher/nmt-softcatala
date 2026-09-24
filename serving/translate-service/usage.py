#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright (c) 2017 Jordi Mas i Hernandez <jmas@softcatala.org>
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

import datetime
import logging

'''
    This class keeps a log of the usage of a service
        - For usage write a line on the file with the date
        - At the number of days specified cleans old entries
'''
class Usage(object):

    FILE = "/srv/data/usage.txt"
    DAYS_TO_KEEP = 7
    rotate = True

    def _set_filename(self, filename):
        self.FILE = filename

    def _get_time_now(self):
        return datetime.datetime.utcnow()

    def get_date_from_line(self, line):
         return line.split("\t", 1)[0]

    def log(self, model_name, words, time_used, _type):
        try:
            with open(self.FILE, "a+") as file_out:
                current_time = self._get_time_now().strftime('%Y-%m-%d %H:%M:%S')
                file_out.write('{0}\t{1}\t{2}\t{3}\t{4}\n'.format(current_time, model_name, words, time_used.total_seconds(), _type))

            if self.rotate and self._is_old_line(self._read_first_line()):
                self._rotate_file()
        except Exception as exception:
            logging.error("log. Error:" + str(exception))
            pass

    def get_stats(self, date_requested):
        results = {}
        try:
            with open(self.FILE, "r") as file_in:
                for line in file_in:
                    date_component, model_component, words_component, time_component, _type = line.strip().split("\t")
                    stats = results.setdefault(model_component, {"calls": 0, "words": 0, "time_used": 0, "files": 0})
                    line_datetime = datetime.datetime.strptime(date_component, '%Y-%m-%d %H:%M:%S')
                    if line_datetime.date() == date_requested.date():
                        if _type == 'file':
                            stats["files"] += 1
                        else:
                            stats["calls"] += 1
                            stats["words"] += int(words_component)
                            stats["time_used"] += float(time_component)

        except Exception as exception:
            logging.error("get_stats. Error:" + str(exception))

        return results

    def _read_first_line(self):
        try:
            with open(self.FILE, "r") as f:
                first = f.readline()
                return first
        except IOError:
            return None

    def _is_old_line(self, line):
        if line is None:
            return False

        line = self.get_date_from_line(line)
        line_datetime = datetime.datetime.strptime(line, '%Y-%m-%d %H:%M:%S')
        return line_datetime < self._get_time_now() - datetime.timedelta(days = self.DAYS_TO_KEEP)

    def _rotate_file(self):
        with open(self.FILE, "r") as f:
            lines = [line for line in f if not self._is_old_line(line)]

        with open(self.FILE, "w") as f:
            f.writelines(lines)
