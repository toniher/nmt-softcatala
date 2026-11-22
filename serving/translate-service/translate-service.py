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

from flask import Flask, request
from flask_cors import CORS
import datetime
from nmt_sc.ctranslate import CTranslate
from usage import Usage
from batchfilesdb import BatchFilesDB
import os
import re
import uuid
import logging
import logging.handlers
import psutil
import threading
from genderbiasdetection import GenderBiasDetectionFactory
from engineselector import select_model, available_pairs, resolve_engine
from languages import langpair_to_iso639_3, language_name

app = Flask(__name__)
app.json.sort_keys = False  # Flask sorts keys by default; keep insertion order
CORS(app)

MODELS = '/srv/models/'
MODELS_AINA = '/srv/models-aina/'
UPLOAD_FOLDER = '/srv/data/files/'

# Translation engines (model families), each a dict keyed by ISO 639-3 pair.
# "softcatala" is the default and the fallback for any other engine.
DEFAULT_ENGINE = "softcatala"
ENGINES = {"softcatala": {}, "aina": {}}

# Per-worker stats (gunicorn runs several workers; /health reports its own pid's numbers).
# Guarded by a lock because each worker serves requests from several threads.
stats_lock = threading.Lock()
translate_calls = 0
total_seconds = 0
translate_chars = 0
total_words = 0

def _load_engine(engine, models_path):
    if not os.path.isdir(models_path):
        print(f"No models for engine '{engine}' at {models_path}, skipping")
        return

    model_directories = next(os.walk(models_path))[1]
    for model_dir in model_directories:
        print(f"[{engine}] Model dir: {model_dir}")
        ENGINES[engine][model_dir] = CTranslate(f"{models_path}", model_dir)

    print(f"[{engine}] {len(ENGINES[engine])} models loaded")


def load_models():
    _load_engine("softcatala", MODELS)
    _load_engine("aina", MODELS_AINA)



def init_logging(logfile):
    logging.basicConfig(
        level=os.environ.get('LOGLEVEL', 'INFO').upper(),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.handlers.RotatingFileHandler(logfile, maxBytes=1024*1024, backupCount=1),
                  logging.StreamHandler()])


@app.route('/translate', methods=['GET'])
def apertium_translate_get():
    return apertium_translate_process(request.args)

@app.route('/health', methods=['GET'])
def health_get():
    health = {}
    rss = psutil.Process(os.getpid()).memory_info().rss // 1024 ** 2
    health['id'] = os.getpid()
    health['rss'] = f"{rss} MB"
    with stats_lock:
        health['average_time_per_request'] = total_seconds / translate_calls if translate_calls else 0
        health['translate_calls'] = translate_calls
        health['words_per_second'] = total_words / total_seconds if total_seconds else 0
        health['average_chars'] = translate_chars // translate_calls if translate_calls else 0
    return health

# This should become /translate once front calls the right API endpoint
@app.route('/translate/', methods=['POST'])
def translate_api():
    return apertium_translate_process(request.form)

def _get_bias_message_if_needed(languages, text, result):
    try:
        bias_detector = GenderBiasDetectionFactory.get(languages=languages)
        if bias_detector:
            bias_words = bias_detector.get_words(text)
            if len(bias_words) > 0:
                source_language = languages[0:3]
                name = language_name(source_language, "ca") or f"'{source_language}'"
                words = ', '.join(bias_words)
                msg = f'Atenció: tingueu present que el text original en {name} conté substantius que poden designar '
                msg += f'persones sense marca de gènere, com ara «{words}». Adapteu-ne la traducció si és necessari.'
                result['message'] = msg
    except Exception as e:
        logging.error(f"_get_bias_message_if_needed. Error: {e}")

    return result

def apertium_translate_process(values):
    global translate_calls, translate_chars, total_seconds, total_words

    start_time = datetime.datetime.now()

    text = values.get('q')
    langpair = values.get('langpair')
    if text is None or not langpair:
        return _bad_request("Cal especificar els paràmetres 'q' i 'langpair'")

    engine = values.get('engine')
    languages = langpair_to_iso639_3(langpair)

    openNMT = select_model(ENGINES, DEFAULT_ENGINE, languages, engine)
    if openNMT is None:
        return _bad_request("No podem traduir en aquest parell de llengües")

    translated = openNMT.translate_parallel(text)

    result = {}
    result = _get_bias_message_if_needed(languages, text, result)

    time_used = datetime.datetime.now() - start_time
    words = len(text.split(' '))
    usage = Usage()
    usage.log(languages, words, time_used, 'form')

    with stats_lock:
        translate_calls += 1
        total_seconds += time_used.total_seconds()
        total_words += words
        translate_chars += len(text)

    logging.debug(f"/translate - time {time_used} - langpair: {langpair} - words: {words}")
    responseData = {}
    responseData['translatedText'] = translated
    result['responseStatus'] = 200
    result['responseData'] = responseData
    result['time'] = str(time_used)
    return result

@app.route('/stats/', methods=['GET'])
def stats():
    try:
        requested = request.args.get('date')
        date_requested = datetime.datetime.strptime(requested, '%Y-%m-%d')
    except Exception as e:
        return {}, 400

    usage = Usage()
    result = usage.get_stats(date_requested)

    return result


@app.route('/version/', methods=['GET'])
def version_api():

    result = {}
    engine = resolve_engine(ENGINES, DEFAULT_ENGINE, request.args.get('engine'))

    for model in ENGINES[engine].values():
        result[model.get_model_name()] = model.get_model_description()

    return result

def _allowed_file(filename):
    ALLOWED_EXTENSIONS = ['txt', 'po']
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file_to_process(filename, email, model_name):
    db = BatchFilesDB()
    db.create(filename, email, model_name)

@app.route('/translate_file/', methods=['POST'])
def upload_file():
    file = request.files['file'] if 'file' in request.files else ""
    email = request.values['email'] if 'email' in request.values else ""
    model_name = request.values.get('model_name', '')

    if model_name not in ENGINES[DEFAULT_ENGINE]:
        return _bad_request("No podem traduir en aquest parell de llengües")

    if file == "" or file.filename == "":
        return _bad_request("No s'ha especificat el fitxer")

    if email == "":
        return _bad_request("No s'ha especificat el correu")

    # Whitespace/control chars would corrupt the tab/line-based batch record
    # (crash-looping translate-batch) and allow e-mail header injection.
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return _bad_request("El correu no és vàlid")

    if not _allowed_file(file.filename):
        return _bad_request("Només s'admeten fitxers .txt i .po")

    fullname = os.path.join(UPLOAD_FOLDER, uuid.uuid4().hex)
    file.save(fullname)

    save_file_to_process(fullname, email, model_name)
    logging.debug("Saved file {0}".format(fullname))
    Usage().log(model_name, 0, datetime.timedelta(), 'file')
    return []


def _bad_request(explanation):
    return {"status": "error", "code": 400, "message": "Bad Request", "explanation": explanation}, 400


@app.route('/listLanguageNames', methods=['GET'])
def list_language_names():
    languages = request.args.get('languages', '').split()
    locale = request.args.get('locale', 'en')

    result = {}
    for language in languages:
        name = language_name(language, locale)
        if name:
            result[language] = name
    return result

@app.route('/listPairs', methods=['GET'])
def list_pairs():

    result = {}
    responseData = []

    for pair in available_pairs(ENGINES, DEFAULT_ENGINE, request.args.get('engine')):
        src, trg = pair.split("-")

        pair = { "sourceLanguage": src,
                 "targetLanguage": trg}
        responseData.append(pair)

    result['responseStatus'] = 200
    result['responseData'] = responseData
    return result


if __name__ == '__main__':
#    app.debug = True
    init_logging('translate-service.log')
    load_models()
    app.run()

if __name__ != '__main__':
    load_models()
    init_logging('translate-service.log')
