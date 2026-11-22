FROM python:3.12.9-slim-bookworm

WORKDIR /srv
RUN --mount=type=bind,source=use-models-tools,target=/src,rw \
    pip install --no-cache-dir /src

COPY use-models-tools/docker/entry-point.sh ./

# Models are mounted at runtime under /srv/models, e.g.:
#   docker run -v "$(pwd)":/srv/files -v /path/to/models-data:/srv/models ...

ENTRYPOINT ["/srv/entry-point.sh"]
