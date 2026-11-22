FROM python:3.12.16-slim-bookworm

WORKDIR /srv
COPY serving/translate-service/requirements.txt .
# use-models-tools is bind-mounted only for the install, so its sources don't end up in the image.
RUN --mount=type=bind,source=use-models-tools,target=/use-models-tools,rw \
    pip install --no-cache-dir -r requirements.txt

COPY serving/translate-service/*.py serving/translate-batch/batchfilesdb.py \
     serving/translate-service/docker/entry-point.sh serving/translate-service/???-gender* ./

# Models are mounted at runtime under /srv/models (see compose.yml / Makefile).

EXPOSE 8700

ENTRYPOINT ["/srv/entry-point.sh"]
