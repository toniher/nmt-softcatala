FROM python:3.12.9-slim-bookworm

WORKDIR /srv
COPY serving/translate-batch/requirements.txt .
# use-models-tools is bind-mounted only for the install, so its sources don't end up in the image.
RUN --mount=type=bind,source=use-models-tools,target=/use-models-tools,rw \
    pip install --no-cache-dir -r requirements.txt

COPY serving/translate-batch/*.py serving/translate-batch/docker/entry-point.sh ./

# Models are mounted at runtime under /srv/models (see compose.yml / Makefile).

ENTRYPOINT ["/srv/entry-point.sh"]
