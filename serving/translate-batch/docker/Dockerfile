FROM python:3.12.9-slim-bookworm AS build

# gcc is only needed to build regex==2021.4.4 (no Python 3.12 wheel); it stays in this stage.
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY use-models-tools/ /use-models-tools/
COPY serving/translate-batch/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.9-slim-bookworm

COPY --from=build /install /usr/local

WORKDIR /srv
COPY serving/translate-batch/*.py serving/translate-batch/docker/entry-point.sh ./

# Models are mounted at runtime under /srv/models (see compose.yml / Makefile).

ENTRYPOINT ["/srv/entry-point.sh"]
