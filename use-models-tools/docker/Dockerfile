FROM python:3.12.9-slim-bookworm AS build

# gcc is only needed to build regex==2021.4.4 (no Python 3.12 wheel); it stays in this stage.
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY use-models-tools/requirements.txt use-models-tools/setup.py ./
COPY use-models-tools/nmt_sc/ nmt_sc/
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12.9-slim-bookworm

COPY --from=build /install /usr/local

WORKDIR /srv
COPY use-models-tools/docker/entry-point.sh ./

# Models are mounted at runtime under /srv/models, e.g.:
#   docker run -v "$(pwd)":/srv/files -v /path/to/models-data:/srv/models ...

ENTRYPOINT ["/srv/entry-point.sh"]
