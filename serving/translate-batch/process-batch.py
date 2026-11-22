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

import contextlib
import logging
import logging.handlers
import os
import subprocess
from batchfilesdb import BatchFilesDB
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

TRANSLATION_MODELS = '/srv/models/'

def init_logging(logfile):
    logging.basicConfig(
        level=os.environ.get('LOGLEVEL', 'INFO').upper(),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.handlers.RotatingFileHandler(logfile, maxBytes=1024*1024, backupCount=1),
                  logging.StreamHandler()])

SENDER_EMAIL = "serveis@softcatala.org"
SUBJECT = "Traducció de Softcatalà"
FAILURE_TEXT = ("No hem pogut traduir el fitxer que ens heu enviat. Comproveu que sigui un fitxer "
                "de text (.txt) o PO (.po) vàlid i torneu-ho a provar més tard.")


def _send(email, message):
    message["Subject"] = SUBJECT
    message["From"] = SENDER_EMAIL
    message["To"] = email
    with smtplib.SMTP("mail.scnet", 25) as server:
        server.sendmail(SENDER_EMAIL, email, message.as_string())


def send_email(translated_file, email, attachment):
    message = MIMEMultipart("alternative")
    if attachment:
        with open(translated_file, mode='rb') as file:
            translation = file.read()

        message.attach(MIMEText("Aquí teniu la traducció que heu demanat", "plain"))
        part = MIMEApplication(translation, Name="ca.po")
        part['Content-Disposition'] = 'attachment; filename=ca.po'
        message.attach(part)
    else:
        with open(translated_file, encoding='utf-8', mode='r') as file:
            message.attach(MIMEText(file.read(), "plain"))

    _send(email, message)


def send_failure_email(email):
    """Tell the user the job failed, so they are not left waiting for a translation that never comes."""
    try:
        _send(email, MIMEText(FAILURE_TEXT, "plain"))
    except Exception as e:
        logging.error(f"Error sending failure notice to {email}: {e}")


def _is_po_file(filename):

    try:
        msgid = False
        msgstr = False
        with open(filename, "r") as read_file:
            lines = 0
            while True:

                src = read_file.readline().lower()

                if not src or lines > 50:
                    break

                if 'msgid' in src:
                    msgid = True

                if 'msgstr' in src:
                    msgstr = True

                if msgid and msgstr:
                    return True

                lines += 1

    except Exception as e:
        msg = "_is_po_file. Error '{0}'".format(e)
        logging.error(msg)

    return False


def process_job(batchfile):
    source_file = batchfile.filename
    translated_file = source_file + "-translated.txt"
    try:
        if _is_po_file(source_file):
            command = 'model_to_po'
            attachment = True
        else:
            command = 'model_to_txt'
            attachment = False

        cmd = [command, '-f', source_file, '-t', translated_file,
               '-m', batchfile.model_name, '-x', TRANSLATION_MODELS]
        logging.debug(f"Run {cmd}")
        subprocess.run(cmd, check=True)
        send_email(translated_file, batchfile.email, attachment)
    except Exception as e:
        logging.error(f"Error processing {source_file}: {e}")
        send_failure_email(batchfile.email)
    finally:
        # Always drop the job so a failing one is not retried forever.
        for path in (batchfile.filename_dbrecord, source_file, translated_file):
            with contextlib.suppress(FileNotFoundError):
                os.remove(path)


def main():

    print("Process batch files to translate")
    init_logging('process-batch.log')
    db = BatchFilesDB()

    while True:
        for batchfile in db.select():
            process_job(batchfile)

        time.sleep(10)


if __name__ == "__main__":
    main()
