# Introduction

This repository contains the Neural Machine Translation tools and models built at Softcatalà. The models are trained with [OpenNMT-tf 2](https://github.com/OpenNMT/OpenNMT-tf) and [TensorFlow 2](https://www.tensorflow.org/), and run with [CTranslate2](https://github.com/OpenNMT/CTranslate2).

All the models built by Softcatalà are published at https://github.com/Softcatala/nmt-models.

# Description of the directories

* *data-processing-tools*: scripts that convert corpora (TMX, PO, WikiMatrix) into OpenNMT plain-text training format
* *gender-bias-detection*: scripts that derive the gender-bias term lists used by the translation API
* *models*: model manifests and download scripts (`models.list`, `aina-models.list`)
* *serving*: the translation API microservice, plus its batch worker and sample HTML client
* *use-models-tools*: library and CLI tools to translate text files or PO files with the models

# Requirements

You need [Docker](https://www.docker.com/) (including the Docker Compose plugin, invoked as `docker compose`) and [Make](https://www.gnu.org/software/make/).

# Downloading the models

The models are **not** built into the Docker images. You download them once into `./models-data/`, and the containers mount that directory read-only. This keeps the images small and lets you choose which language pairs to include.

```sh
# All the models listed in models/models.list
make download-models

# ...or only the language pairs you need
make download-models MODELS="eng-cat cat-eng"
```

There is one directory per language pair (e.g. `eng-cat`). The download runs inside a throwaway container, so Docker is all you need. Pairs already up to date are skipped, so you can re-run the command safely.

## Updating the models

`models/models.list` pins one dated zip per language pair. To see whether newer models have been published, and whether the installed ones match the manifest:

```sh
make check-models
```

To update a pair, change its line in `models/models.list` to the new zip name, run `make download-models` again and restart the services (they load the models at startup). The download replaces any pair whose installed date differs from the manifest and skips the rest.

AINA models work the same way. Their version is a fingerprint of the model files on HuggingFace. A line in `models/aina-models.list` follows the latest release unless a commit is added as a third column to pin it.

## Optional: AINA models

The API can also serve the [AINA](https://langtech-bsc.gitbook.io/aina-kit/models/models-de-traduccio-automatica) translation models, built by Projecte Aina (Barcelona Supercomputing Center) and published on HuggingFace. They go into a separate `./models-data-aina/` directory:

```sh
# All the models listed in models/aina-models.list
make download-aina-models

# ...or only selected pairs
make download-aina-models MODELS="eng-cat cat-eng"
```

Without them, the API simply uses the Softcatalà models. With them, a client chooses AINA per request by adding `engine=aina`. If there is no AINA model for the requested pair, the Softcatalà one is used instead.

# Running the translation API

## With Docker Compose (recommended)

This starts the `translate-service` webserver (the HTTP API) and the `translate-batch` worker (which translates uploaded files) as in production, using [`compose.yml`](./compose.yml).

1. Download the models (see above).

2. Build the images:

   ```sh
   make build-all
   ```

3. Start the services in the background:

   ```sh
   make docker-run-all-services      # runs: docker compose up -d
   ```

   The API listens on port **8700**. Try it with curl. Single-quote the URL, so your shell doesn't treat `|` as a pipe or `!` as history expansion:

   ```sh
   curl 'http://localhost:8700/translate?langpair=en|ca&q=Hello!'
   curl 'http://localhost:8700/translate?langpair=en|ca&q=Hello!&engine=aina'   # with AINA models
   ```

   `docker compose logs -f` shows the requests as they come in.

4. Stop the services:

   ```sh
   docker compose down
   ```

Compose creates its own network. To join a shared external network instead, as in production, uncomment the `networks` block in [`compose.yml`](./compose.yml).

## Only the API webserver

To run the HTTP API without the batch worker:

```sh
make docker-build-translate-service
make docker-run-translate-service
```

It mounts `./models-data` and `./models-data-aina` for you. File uploads (`/translate_file/`) are accepted but never processed, because there is no batch worker to translate them.

# The API

## Apertium-compatible methods

Translators can plug machine translation straight into their existing tools. The service implements the [Apertium Web API](https://wiki.apertium.org/wiki/Apertium-apy), so any tool with Apertium support works with it. We've tested the Okapi Framework and the OmegaT translation plugin.

| Method | Verb | Parameters |
| --- | --- | --- |
| `/translate` | GET | `langpair` (e.g. `en\|ca`, 2- or 3-letter codes), `q` (the text, up to 20,000 characters), optional `engine` (`aina`) |
| `/translate/` | POST | same as GET, as form fields (a POST to `/translate` is redirected here) |
| `/listPairs` | GET | optional `engine` |
| `/listLanguageNames` | GET | `languages` (space-separated 3-letter codes), optional `locale` (`ca` for Catalan names, English otherwise) |

The translation is in `responseData.translatedText`. For English and Basque source texts, the response can also carry a `message`: a notice in Catalan listing nouns that may refer to people without marking their gender, so the translation may need adapting.

## Other methods

| Method | Verb | What it does |
| --- | --- | --- |
| `/translate_file/` | POST | Queues a `.txt` or `.po` file (`file`, up to 8 MB) for translation with `model_name` (e.g. `eng-cat`). The result is emailed to `email` |
| `/version/` | GET | Description and test scores of each loaded model (optional `engine`) |
| `/health` | GET | Memory use and request statistics of the process that answers |
| `/stats/` | GET | Calls, words and files per language pair on `date` (`YYYY-MM-DD`; the last 7 days are kept) |

`serving/html-client/` is a sample web page that uses these methods.

# Using the models in your machine

Use this to translate large volumes with the same models that run in production. Download the models you need and build the command line tool:

```sh
make download-models MODELS="eng-cat cat-eng"
make docker-build-use-models-tools
```

The commands below mount your current directory (the files to translate) at `/srv/files` and the models at `/srv/models`. `-m` names the model to use, and it must be a pair you downloaded into `models-data/`.

To translate a text file:

```sh
echo "Hello World" > input.txt
docker run -it --rm \
  -v "$(pwd)":/srv/files/ \
  -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f input.txt -t output.txt -m eng-cat" \
  use-models-tools
more output.txt
```

Use `-m cat-eng` to translate from Catalan to English instead.

To translate a PO file (here `ca.po`), set `FILE_TYPE=po`:

```sh
docker run -it --rm \
  -v "$(pwd)":/srv/files/ \
  -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f ca.po -m eng-cat" --env FILE_TYPE='po' \
  use-models-tools
```

The translation is written to `ca.po-ca.po`; add `-t <file>` to choose another name.

# Development

## Tests

The unit tests run on your machine with Python 3.12:

```sh
pip install nose2==0.16.0 -r use-models-tools/requirements.txt
make run-tests
```

The API tests run inside a container against a live service. They need the `eng-cat`, `cat-eng` and `eus-cat` models:

```sh
make download-models MODELS="eng-cat cat-eng eus-cat"
make docker-build-translate-service-test
make docker-run-translate-service-test
```

## Performance test

`serving/perf-tests/tune.sh` load-tests the translation service with `wrk`. It starts its own service container and runs `wrk` in another, so it needs only Docker, the `translate-service` image and the `eng-cat` model:

```sh
make docker-build-translate-service
make download-models MODELS=eng-cat
serving/perf-tests/tune.sh 2:4:1:6    # the default layout (WORKERS:THREADS:INTER:INTRA)
```

For a short sentence and a paragraph, at 1, 4, 8 and 16 concurrent connections, it reports requests per second, median and p99 latency, and errors. It also reports the container's memory.

Before shipping changes that could affect translation speed, run it on the same host before and after the change, and compare.

## Tuning for a host

How many processes and threads to use depends on the host's CPUs and memory. [serving/TUNING.md](serving/TUNING.md) explains the settings and gives starting points by host size and reference measurements. To compare layouts on the host itself, give `tune.sh` several of them: `serving/perf-tests/tune.sh 2:4:1:6 1:8:4:3 1:8:6:2`.

# License

See [license](./LICENSE.md)

# Contact

Email address: Jordi Mas: jmas@softcatala.org
