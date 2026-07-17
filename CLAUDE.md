# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Introduction

Neural Machine Translation tools and models built at Softcatalà using CTranslate2 (models are trained with OpenNMT-tf 2 / TensorFlow 2, then exported for CTranslate2 inference). Everything is Python 3.12, Docker-based, and built/tested with `make`.

Models are **not** baked into images. They are downloaded once into a local `models-data/` directory (gitignored) and bind-mounted read-only into the containers at `/srv/models`. Service/batch/CLI images contain code only.

Two model families ("engines") are supported by the translate-service: the default **Softcatalà** models (`/srv/models`) and, optionally, **AINA** (Projecte Aina / BSC) models downloaded from HuggingFace into `models-data-aina/` and mounted read-only at `/srv/models-aina`. AINA models are also CTranslate2 + SentencePiece, so the same `nmt_sc.ctranslate.CTranslate` loader serves both. A caller opts into AINA with `&engine=aina` on `/translate`; if no AINA model exists for the requested pair it silently falls back to the Softcatalà one (omitting `engine` always uses Softcatalà).

## Repository layout

- `models/` — model provisioning (no Docker image). `models.list` is the checked-in default set of model zip filenames (pair = first 7 chars of the filename, e.g. `eng-cat`; comment a line out to exclude it). `download-models.sh` reads that manifest, optionally filters it by a `MODELS="eng-cat cat-eng"` variable, and downloads/unzips the selected pairs into `models-data/` inside a throwaway Debian container (host needs only Docker; already-present pairs are skipped; files are chowned back to the host user). `generate-manifest.py` scrapes the published index and prints an updated `models.list` when new models are released. `aina-models.list` + `download-aina-models.sh` do the same for the AINA family: the manifest holds `<huggingface_repo_id> <pair>` lines, and the script (throwaway `python:3.12-slim` container using `huggingface_hub`) downloads each repo and **normalizes** it into the Softcatalà layout below (`ctranslate2/`, `tokenizer/sp_m.model`, generated `metadata/model_description.txt`) under `models-data-aina/`. The manifest ships with `eng-cat`/`cat-eng` active and five additional language families commented out: `spa`, `fra`, `deu`, `ita`, `por` ↔ `cat`. **Note**: `fra`, `deu`, and `por` pairs are already in `LANGUAGE_ALIASES` (the service inherits them from Softcatalà); `spa` and `ita` are not — enabling those AINA pairs also requires adding entries to `LANGUAGE_ALIASES` in `serving/translate-service/translate-service.py`.
- `use-models-tools/` — the core Python library (`nmt_sc` package) that wraps CTranslate2 for translation, plus CLI entry points `model_to_po` and `model_to_txt` (registered via `setup.py`). This package is installed (via `../use-models-tools` in `requirements.txt` or by copying `nmt_sc/`) into both `translate-service` and `translate-batch`, then deleted from the batch/service Docker layers after `pip install` to keep images slim.
- `serving/translate-service/` — Flask microservice (`translate-service.py`) exposing an Apertium-compatible API (`/translate`, `/listLanguageNames`, `/listPairs`) plus `/health`, `/stats/`, `/version/`, `/translate_file/`. At startup it loads every model directory under `/srv/models/` (and, if present, `/srv/models-aina/`) into the `ENGINES` registry — `{"softcatala": {pair: model}, "aina": {...}}`, keyed by ISO 639-3 language pair (e.g. `eng-cat`). The optional `engine` request param selects the family; `engineselector.select_model()` (a small dependency-free helper, unit-tested in `tests/testengineselector.py`) resolves it with Softcatalà fallback. Includes gender-bias detection (`genderbiasdetection.py`) that appends a Catalan-language advisory when the source text (English or Basque) contains gender-ambiguous nouns.
- `serving/translate-batch/` — background worker (`process-batch.py`) that polls `batchfilesdb.py` (SQLite-backed queue) for files uploaded via `/translate_file/`, translates them by shelling out to `model_to_po`/`model_to_txt`, and emails the result via local SMTP (`mail.scnet`).
- `serving/html-client/` — static HTML sample client for the translate-service API.
- `serving/perf-tests/` — `wrk`-based performance test script for the translation service.
- `data-processing-tools/` — standalone scripts to convert corpora (TMX, PO, WikiMatrix) into OpenNMT plain-text training format; not wired into the Docker builds.
- `gender-bias-detection/` — `extract-terms.py` derives the gender-bias term lists (consumed by `serving/translate-service/genderbiasdetection.py`) from the `mt_gender` dataset; the Basque list also goes through an `awk` regex-generation step.

## Build and run

Requires Docker and Make. Image builds no longer download models — build is fast and model download is a separate, one-time step.

```bash
# 1. Download models into ./models-data (default set from models/models.list)
make download-models                    # all models in the manifest
make download-models MODELS="eng-cat cat-eng"   # only selected pairs
#   MODELS_DIR=... overrides the target dir; MODELS_URL=... the source

# 1b. (optional) Download AINA models into ./models-data-aina (from models/aina-models.list)
make download-aina-models                       # all pairs in the AINA manifest
make download-aina-models MODELS="eng-cat cat-eng"   # only selected pairs
#   MODELS_AINA_DIR=... overrides the target dir

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
make docker-run-all-services            # docker compose up -d (compose.yml): both services detached, models-data mounted read-only
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
This runs `nose2` in three independent locations — `use-models-tools`, `serving/translate-batch`, `serving/translate-service` — each treated as its own test root (imports are relative to that directory, not the repo root). To run a single suite or test, `cd` into the relevant directory first, e.g.:
```bash
cd use-models-tools && python -m nose2 testctranslate
cd serving/translate-service && python -m nose2 testgenderbiasdetection.TestGenderBiasDetection.test_some_case
```
CI (`.gitlab-ci.yml`) runs the same tests against `python:3.12.9-slim-bookworm` before any Docker images are built, then builds/pushes `translate-service` → `translate-batch` / `use-models-tools`. The `translate-service-test` job needs real models to translate: because it runs under `docker:dind` (where host bind-mounts aren't visible to the daemon), it downloads `eng-cat`/`cat-eng` into a **named volume** and mounts that into the test container, rather than using `models-data/`.

## Key conventions

- **Language pairs** are identified by 3-letter ISO 639-3 codes joined with a hyphen, lowercase (`eng-cat`, `cat-deu`), matching model directory names under `/srv/models/`. The service's `LANGUAGE_ALIASES` dict (in `translate-service.py`) translates the Apertium `xx|yy` 2/3-letter query format to this internal key. Currently covers `eng`, `deu`, `fra`, `por` ↔ `cat`; `spa` and `ita` are absent and must be added before those pairs are usable via the API.
- **Model directory layout** expected by `nmt_sc.ctranslate.CTranslate`: `<models_path>/<model_name>/ctranslate2/` (the CTranslate2 model), `<models_path>/<model_name>/tokenizer/sp_m.model` (SentencePiece model), `<models_path>/<model_name>/metadata/model_description.txt`. AINA models are downloaded into this exact layout by `download-aina-models.sh` (their HF repo instead ships the CT2 files + `spm.model` at the repo root), so both engines share one loader.
- **Engine selection**: the `engine` request param (`softcatala` default, `aina`) chooses the model family; `aina` falls back to the Softcatalà model when the pair is missing. Resolution lives in `serving/translate-service/engineselector.py` (kept import-light so it is unit-testable without Flask, which CI's `tests` job does not install).
- CTranslate2 runtime tuning is via env vars: `CTRANSLATE_INTER_THREADS`, `CTRANSLATE_INTRA_THREADS`, `CTRANSLATE_BEAM_SIZE`, `CTRANSLATE_USE_VMAP`, `DEVICE` (`cpu`/`cuda`) — see `use-models-tools/nmt_sc/ctranslate.py`.
- Translation goes through sentence splitting/tokenization (`texttokenizer.py`, `srx_segmenter.py`) and markup preservation (`preservemarkup.py`) before/after the CTranslate2 batch call, so raw text and PO/HTML-ish markup round-trip correctly.
- Gender-bias detection only fires for `eng-cat` and `eus-cat` source pairs (`GenderBiasDetectionFactory`); its term lists are data files, not code — regenerate them via `make generate-bias-terms` if the source dataset changes.
