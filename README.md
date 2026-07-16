# Introduction

This repository contains Neural Machine Translation tools and models built at Softcatalà using [OpenNMT-tf 2](https://github.com/OpenNMT/OpenNMT-tf) and [TensorFlow 2](https://www.tensorflow.org/)

# Description of the directories

* *data-processing-tools*: set of data processing tools that convert for different formats to OpenNMT plain text input format
* *serving*: contains a microservice that provides a translation API for web service and batch file processing.
* *use-models-tools*: contains tools to use the models to translate text files or PO files
* *evaluate*: set of tools and corpus to evaluate different translation systems (including BLEU scores)
* *training*: scripts and configurations to train the models

# Models

All the Softcatalà built models are available here: https://github.com/Softcatala/nmt-models

# Serving

## Requirements

You need [Docker](https://www.docker.com/) (including the Docker Compose plugin, invoked as `docker compose`) and [Make](https://www.gnu.org/software/make/), for which there are different implementations depending on your operating system.

## How the models are provided

The translation models are **not** built into the Docker images. Instead they are downloaded once into a local `models-data/` directory and mounted read-only into the containers at runtime. This keeps the images small and lets you choose exactly which language pairs to include.

Download the models before building or running anything:

```bash
# Download the default set of models listed in models/models.list
make download-models

# ...or download only the language pairs you need
make download-models MODELS="eng-cat cat-eng"
```

Models land in `./models-data/` (one directory per language pair, e.g. `eng-cat`). The download runs inside a throwaway container, so you only need Docker installed. Already-downloaded pairs are skipped, so the command is safe to re-run.

## Raising the translation API webserver with Docker Compose

This is the recommended way to run the translation API. It starts the `translate-service` webserver (the HTTP API) together with the `translate-batch` worker, exactly as in production, using [`compose.yml`](./compose.yml).

1. Download the models you want (see above):

   ```bash
   make download-models MODELS="eng-cat cat-eng"
   ```

2. Build the service images:

   ```bash
   make build-all
   ```

3. Start the services in the background:

   ```bash
   make docker-run-all-services      # runs: docker compose up -d
   ```

   The API is now listening on port **8700**. Test it with curl (single-quote the URL so your shell doesn't treat `|` as a pipe or expand `!` as history substitution):

   ```bash
   curl 'http://localhost:8700/translate?langpair=en|ca&q=Hello!'
   ```

   Follow the logs with `docker compose logs -f` if you want to watch requests.

4. Stop the services:

   ```bash
   docker compose down
   ```

The compose file uses Compose's automatic default network. If you prefer to run the services on a shared external network (as in production), uncomment the `networks` block in [`compose.yml`](./compose.yml).

### Running only the API webserver

If you just want the HTTP API without the batch worker, run the single service directly (it mounts `./models-data` for you):

```bash
make download-models MODELS="eng-cat cat-eng"
make docker-build-translate-service
make docker-run-translate-service
curl 'http://localhost:8700/translate?langpair=en|ca&q=Hello!'
```


## Apertium API

One of the use cases for Machine Translation is to use it to speed up the work of translators.

In order to integrate easily with already existing translation tools we support the [Apertium Web API](https://wiki.apertium.org/wiki/Apertium-apy). This means that you can use any tool that has support for Apertium.

We confirm that the following tools work using Apertium pluggins:

* Okapi Framework
* OmegaT translation plugin

**Supported methods**

| Method | Verb
|---|---|
|/translate  | GET or POST
|/listLanguageNames  | GET
|/listPairs  | GET

# Using the models in your machine

This is useful for example if you want to translate large volumes using our prebuild English - Catalan models using the same exact version that we have in production.

First download the models you need and build the command line tool:

```bash
make download-models MODELS="eng-cat cat-eng"
make docker-build-use-models-tools
```

Every command below mounts your current directory (the files to translate) at `/srv/files` and the downloaded models at `/srv/models`.

To test quickly that everything works:
```bash
echo "Hello World" > input.txt
docker run -it --rm \
  -v "$(pwd)":/srv/files/ \
  -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f input.txt -t output.txt -m eng-cat" \
  use-models-tools
more output.txt
```

To translate PO files (with `ca.po` in your current directory):
```bash
docker run -it --rm \
  -v "$(pwd)":/srv/files/ \
  -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f ca.po -m eng-cat" --env FILE_TYPE='po' \
  use-models-tools
```
The translated file will be `ca.po-ca.po`.

To translate a text file from Catalan to English:
```bash
echo "Hola món" > input.txt
docker run -it --rm \
  -v "$(pwd)":/srv/files/ \
  -v "$(pwd)/models-data":/srv/models \
  --env COMMAND_LINE="-f input.txt -t output.txt -m cat-eng" \
  use-models-tools
more output.txt
```

Note: the parameter `-m cat-eng` indicates the translation model to use, and it must match a language pair you downloaded into `models-data/`.

# Development

## Performance test of the translation service

It is important to understand that there are no major performance regressions.

Install the ```wrk``` performance testing tool by using ```sudo apt-get install wrk```

Follow these steps:
* Run ```make docker-run-all-services``` to run all the services for the performance test
* Use ```serving/perf-tests``` script to run the performance test

# License

See [license](./LICENSE.md)

# Contact

Email address: Jordi Mas: jmas@softcatala.org
