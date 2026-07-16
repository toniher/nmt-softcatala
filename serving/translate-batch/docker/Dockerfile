FROM python:3.12.9-slim-bookworm as copied_files

COPY serving/translate-batch/requirements.txt /srv/
COPY serving/translate-batch/*.py /srv/
COPY serving/translate-batch/docker/entry-point.sh /srv/

FROM python:3.12.9-slim-bookworm

RUN apt-get update -y && apt-get upgrade -y && apt-get install gcc git -y
RUN apt-get install python3-pip -y --no-install-recommends
RUN pip3 install --upgrade pip && pip3 install --upgrade setuptools

COPY --from=copied_files /srv/ /srv/

# Models are mounted at runtime under /srv/models (see compose.yml / Makefile).

WORKDIR /srv
COPY use-models-tools/ /use-models-tools/
RUN pip3 install -r requirements.txt
RUN rm -r -f use-models-tools/

ENTRYPOINT /srv/entry-point.sh
#ENTRYPOINT bash
