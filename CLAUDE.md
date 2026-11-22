# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Introduction

Neural Machine Translation tools and models built at Softcatalà using CTranslate2 (models are trained with OpenNMT-tf 2 / TensorFlow 2, then exported for CTranslate2 inference). Everything is Python 3.12, Docker-based, and built/tested with `make`.

Models are **not** baked into images. They are downloaded once into a local `models-data/` directory (gitignored) and bind-mounted read-only into the containers at `/srv/models`. Service/batch/CLI images contain code only.

Two model families ("engines") are supported by the translate-service: the default **Softcatalà** models (`/srv/models`) and, optionally, **AINA** (Projecte Aina / BSC) models downloaded from HuggingFace into `models-data-aina/` and mounted read-only at `/srv/models-aina`. AINA models are also CTranslate2 + SentencePiece, so the same `nmt_sc.ctranslate.CTranslate` loader serves both. A caller opts into AINA with `&engine=aina` on `/translate`; if no AINA model exists for the requested pair it silently falls back to the Softcatalà one (omitting `engine` always uses Softcatalà).

## Repository layout

- `models/` — model provisioning (no Docker image). `models.list` is the checked-in default set of model zip filenames (pair = first 7 chars of the filename, e.g. `eng-cat`; comment a line out to exclude it). `download-models.sh` reads that manifest, optionally filters it by a `MODELS="eng-cat cat-eng"` variable, and downloads/unzips the selected pairs into `models-data/` inside a throwaway Debian container (host needs only Docker; files are chowned back to the host user). An installed pair is skipped when the `Date:` in its `metadata/model_description.txt` equals the manifest filename's date, and otherwise replaced via a `.staging/` dir (hidden dirs are ignored by the service loader). `aina-models.list` + `download-aina-models.sh` do the same for the AINA family: the manifest holds `<huggingface_repo_id> <pair> [<commit>]` lines (no commit = `main`); the version is a `Fingerprint:` (sha1 of the HF blob ids of the four files used, so README-only commits don't count) written to the metadata with the `Revision:`, and the script (throwaway `python:3.12-slim` container using `huggingface_hub`) downloads each repo and **normalizes** it into the Softcatalà layout below (`ctranslate2/`, `tokenizer/sp_m.model`, generated `metadata/model_description.txt`) under `models-data-aina/`. The manifest ships with `eng-cat`/`cat-eng` active and five additional language families commented out: `spa`, `fra`, `deu`, `ita`, `por` ↔ `cat`. `check-models.py` (`make check-models`, stdlib-only, in a `python:3.12-slim` container) compares both manifests with the published index / HuggingFace and with what is installed, and changes nothing; updating a model = edit its manifest line, re-run the download, restart the services. Enabling a new language also needs an entry in `LANGUAGES` (`serving/translate-service/languages.py`) for 2-letter `langpair` codes and `/listLanguageNames`; all of these five are already there.
- `use-models-tools/` — the core Python library (`nmt_sc` package) that wraps CTranslate2 for translation, plus CLI entry points `model_to_po` and `model_to_txt` (registered via `setup.py`). This package is installed (via `../use-models-tools` in `requirements.txt` or by copying `nmt_sc/`) into both `translate-service` and `translate-batch`. Images are single-stage on `python:3.12-slim` with no compiler (all deps ship wheels or are pure Python); `use-models-tools/` is BuildKit bind-mounted (`RUN --mount=type=bind`) only for the `pip install`, so its sources never land in the image.
- `serving/translate-service/` — Flask microservice (`translate-service.py`) exposing an Apertium-compatible API (`/translate`, `/listLanguageNames`, `/listPairs`) plus `/health`, `/stats/`, `/version/`, `/translate_file/`. At startup it loads every model directory under `/srv/models/` (and, if present, `/srv/models-aina/`) into the `ENGINES` registry — `{"softcatala": {pair: model}, "aina": {...}}`, keyed by ISO 639-3 language pair (e.g. `eng-cat`). The optional `engine` request param selects the family; `engineselector.select_model()` (a small dependency-free helper, unit-tested in `tests/testengineselector.py`) resolves it with Softcatalà fallback. Includes gender-bias detection (`genderbiasdetection.py`) that appends a Catalan-language advisory when the source text (English or Basque) contains gender-ambiguous nouns.
- `serving/translate-batch/` — background worker (`process-batch.py`) that polls `batchfilesdb.py` (file-per-job queue: one tab-separated record per job under `/srv/data/entries/`) for files uploaded via `/translate_file/`, translates them by shelling out to `model_to_po`/`model_to_txt`, and emails the result via local SMTP (`mail.scnet`).
- `serving/html-client/` — static HTML sample client for the translate-service API.
- `serving/perf-tests/` — `tune.sh`: Docker-only `wrk` load test of translate-service across thread layouts (payloads in `short.lua` / `para.lua`); see `serving/TUNING.md`.
- `data-processing-tools/` — standalone scripts to convert corpora (TMX, PO, WikiMatrix) into OpenNMT plain-text training format; not wired into the Docker builds.
- `gender-bias-detection/` — `extract-terms.py` derives the gender-bias term lists (consumed by `serving/translate-service/genderbiasdetection.py`) from the `mt_gender` dataset; the Basque list also goes through an `awk` regex-generation step.

## Build and run

Requires Docker and Make. Image builds don't download models — build is fast and model download is a separate, one-time step.

```bash
# 1. Download models into ./models-data (default set from models/models.list)
make download-models                    # all models in the manifest
make download-models MODELS="eng-cat cat-eng"   # only selected pairs
#   MODELS_DIR=... overrides the target dir; MODELS_URL=... the source

# 1b. (optional) Download AINA models into ./models-data-aina (from models/aina-models.list)
make download-aina-models                       # all pairs in the AINA manifest
make download-aina-models MODELS="eng-cat cat-eng"   # only selected pairs
#   MODELS_AINA_DIR=... overrides the target dir
#   MODELS_DIR / MODELS_AINA_DIR are honoured by every make target and by compose.yml (${MODELS_DIR:-./models-data});
#   the Makefile makes them absolute, since docker -v treats a relative path as a named volume

# 2. Build the (code-only) images
make build-all                          # use-models-tools, translate-service (+test image), translate-batch
make docker-build-use-models-tools
make docker-build-translate-service
make docker-build-translate-service-test
make docker-build-translate-batch

# 3. Run — models are bind-mounted from ./models-data at /srv/models
make docker-run-translate-service       # run translate-service on :8700
make docker-run-translate-service-test  # run the test image variant
make docker-run-translate-batch         # run the batch worker (needs the traductor-files volume)
make docker-run-all-services            # docker compose up -d (compose.yml): both services detached, models dirs mounted read-only
make check-models                       # newer published models? installed ones out of date?
```

Try it: `http://localhost:8700/translate?langpair=en|ca&q=Hello!`
Try AINA (requires `make download-aina-models`): `http://localhost:8700/translate?langpair=en|ca&q=Hello!&engine=aina`

Using prebuilt models directly (CLI, no service) — mount both your files and the models dir:
```bash
make download-models MODELS="eng-cat"
make docker-build-use-models-tools
docker run -it -v "$(pwd)":/srv/files/ -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f input.txt -t output.txt -m eng-cat" --rm use-models-tools
# FILE_TYPE=po env var switches the entry point to model_to_po instead of model_to_txt
```

## Tests

```bash
make run-tests
```
This runs `nose2` in three independent locations — `use-models-tools`, `serving/translate-batch`, `serving/translate-service` — each treated as its own test root (imports are relative to that directory, not the repo root). Test modules live in each root's `tests/` subdir, so a single suite/test must be addressed as `tests.<module>` (bare `testctranslate` fails to import):
```bash
cd use-models-tools && python -m nose2 tests.testctranslate
cd serving/translate-service && python -m nose2 tests.testgenderbiasdetection.TestGenderBiasDetection.test_some_case
```
nose2 is not in the component `requirements.txt` files; install it separately (`pip install nose2==0.16.0`, same version as CI and `api-tst/requirements.txt`). `serving/translate-service/api-tst/test-apertium.py` is a separate API test that hits a running service at `http://127.0.0.1:8700` (start it with `make docker-run-translate-service` first); it is not part of `make run-tests`.
CI (`.gitlab-ci.yml`) runs the same tests against `python:3.12.16-slim-bookworm` before any Docker images are built, then builds/pushes `translate-service` → `translate-batch` / `use-models-tools`. The `translate-service-test` job needs real models to translate: because it runs under `docker:dind` (where host bind-mounts aren't visible to the daemon), it downloads `eng-cat`/`cat-eng`/`eus-cat` into a **named volume** and mounts that into the test container, rather than using `models-data/`.

## Key conventions

- **Language pairs** are identified by 3-letter ISO 639-3 codes joined with a hyphen, lowercase (`eng-cat`, `cat-deu`), matching model directory names under `/srv/models/`. `languages.py` (`LANGUAGES`: ISO 639-3 → 639-1 code + English/Catalan name) maps each side of the Apertium `xx|yy` query (2- or 3-letter codes) to this internal key, and supplies `/listLanguageNames` (honours `locale=ca`) and the bias-message language name. Unknown codes pass through unchanged.
- **Model directory layout** expected by `nmt_sc.ctranslate.CTranslate`: `<models_path>/<model_name>/ctranslate2/` (the CTranslate2 model), `<models_path>/<model_name>/tokenizer/sp_m.model` (SentencePiece model), `<models_path>/<model_name>/metadata/model_description.txt`. AINA models are downloaded into this exact layout by `download-aina-models.sh` (their HF repo instead ships the CT2 files + `spm.model` at the repo root), so both engines share one loader.
- **Engine selection**: the `engine` request param (`softcatala` default, `aina`) chooses the model family; `aina` falls back to the Softcatalà model when the pair is missing. `/listPairs` and `/version/` accept the same `engine` param (default responses list Softcatalà only). Resolution lives in `serving/translate-service/engineselector.py` (kept import-light so it is unit-testable without Flask, which CI's `tests` job does not install).
- **Request limits** (`translate-service.py`): `q` is capped at `MAX_QUERY_CHARS` (20,000, 400 beyond) and uploads at `MAX_UPLOAD_BYTES` (8 MB, the only size limit on batch jobs; Flask returns a JSON 413 beyond). `html-client/openmnt.js` repeats the 8 MB check because browsers may not surface a 413 sent mid-upload — change both together.
- `usage.py` is written by every gunicorn worker: appends and rotation hold an `flock` on `usage.txt.lock`, and rotation rewrites via temp file + `os.replace`.
- Runtime tuning is via env vars: `GUNICORN_WORKERS`/`GUNICORN_THREADS` (read by `serving/translate-service/docker/entry-point.sh`) and `CTRANSLATE_INTER_THREADS`, `CTRANSLATE_INTRA_THREADS`, `CTRANSLATE_BEAM_SIZE`, `CTRANSLATE_USE_VMAP`, `DEVICE` (`cpu`/`cuda`; read in `use-models-tools/nmt_sc/ctranslate.py`). `serving/TUNING.md` explains how to choose them per host (each worker loads every model; prefer higher INTER with INTRA 2–3), and `serving/perf-tests/tune.sh` benchmarks layouts with Docker-only `wrk`.
- `nmt_sc/segment.srx` holds Java-regex SRX rules; `srx_segmenter.parse()` rewrites Java `\Q…\E` quoting (unsupported by Python's `regex`) — `tests/testtexttokenizer.py` compiles every rule, so run it after editing the SRX file.
- Translation goes through sentence splitting/tokenization (`texttokenizer.py`, `srx_segmenter.py`) and markup preservation (`preservemarkup.py`) before/after the CTranslate2 batch call, so raw text and PO/HTML-ish markup round-trip correctly.
- Every model's SentencePiece vocabulary lacks some characters (e.g. `` _ ` @ | € `` for eng-cat; the set differs per model, see `issue-39.md`). `SentencePieceTokenizer.is_unknown()` detects them; `CTranslate` replaces typographic ones with plain equivalents (`UNKNOWN_CHAR_REPLACEMENTS`) and `PreserveMarkup` swaps the rest, plus inline code and tags, for markers built from characters the model knows (`MARKER_CANDIDATES`). Text without such characters is tokenized exactly as before. `model_to_po._clean_string` strips `_ & ~` only where they are UI accelerators.
- Gender-bias detection only fires for `eng-cat` and `eus-cat` source pairs (`GenderBiasDetectionFactory`); its term lists are data files, not code — regenerate them via `make generate-bias-terms` if the source dataset changes.
