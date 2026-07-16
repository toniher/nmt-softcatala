FROM python:3.12.9-slim-bookworm

RUN apt-get update -y && apt-get upgrade -y && apt-get install gcc vim -y
RUN apt-get install python3-pip -y --no-install-recommends
RUN pip3 install --upgrade pip && pip3 install --upgrade setuptools

COPY use-models-tools/requirements.txt /srv/
COPY use-models-tools/docker/entry-point.sh /srv/
COPY use-models-tools/setup.py /srv/
COPY use-models-tools/nmt_sc/ /srv/nmt_sc/
WORKDIR /srv
RUN pip3 install .

# Models are mounted at runtime under /srv/models, e.g.:
#   docker run -v "$(pwd)":/srv/files -v /path/to/models-data:/srv/models ...

ENTRYPOINT /srv/entry-point.sh
#ENTRYPOINT bash
