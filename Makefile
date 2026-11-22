MODELS_DIR ?= $(PWD)/models-data
MODELS_AINA_DIR ?= $(PWD)/models-data-aina
# docker -v needs absolute paths (a relative one becomes a named volume)
override MODELS_DIR := $(abspath $(MODELS_DIR))
override MODELS_AINA_DIR := $(abspath $(MODELS_AINA_DIR))

build-all: docker-build-use-models-tools docker-build-translate-service docker-build-translate-service-test docker-build-translate-batch

download-models:
	MODELS="$(MODELS)" MODELS_DIR="$(MODELS_DIR)" ./models/download-models.sh

download-aina-models:
	MODELS="$(MODELS)" MODELS_AINA_DIR="$(MODELS_AINA_DIR)" ./models/download-aina-models.sh

# Compares models.list / aina-models.list with what is published and installed (changes nothing).
check-models:
	mkdir -p "$(MODELS_DIR)" "$(MODELS_AINA_DIR)"
	docker run --rm -v "$(PWD)/models":/srv/manifests:ro -v "$(MODELS_DIR)":/srv/models:ro \
	  -v "$(MODELS_AINA_DIR)":/srv/models-aina:ro -e MODELS_URL -e MODELS_DIR=/srv/models \
	  -e MODELS_AINA_DIR=/srv/models-aina python:3.12-slim python -I /srv/manifests/check-models.py

docker-build-use-models-tools:
	docker build -t use-models-tools . -f use-models-tools/docker/Dockerfile;

docker-build-translate-service:
	docker build -t translate-service . -f serving/translate-service/docker/Dockerfile;

docker-build-translate-service-test: docker-build-translate-service
	docker build -t translate-service-test . -f serving/translate-service/docker/Dockerfile-test;

docker-build-translate-batch:
	docker build -t translate-batch . -f serving/translate-batch/docker/Dockerfile;

docker-run-translate-batch:
	docker volume create traductor-files;
	docker run -v traductor-files:/srv/data -v "$(MODELS_DIR)":/srv/models:ro -it --rm translate-batch;

docker-run-translate-service:
	docker run -it --rm -p 8700:8700 -v "$(MODELS_DIR)":/srv/models:ro -v "$(MODELS_AINA_DIR)":/srv/models-aina:ro translate-service;

docker-run-translate-service-test:
	docker run -it --rm -p 8700:8700 -v "$(MODELS_DIR)":/srv/models:ro -v "$(MODELS_AINA_DIR)":/srv/models-aina:ro translate-service-test;

docker-run-all-services:
	MODELS_DIR="$(MODELS_DIR)" MODELS_AINA_DIR="$(MODELS_AINA_DIR)" docker compose up -d;

generate-bias-terms:
	cd gender-bias-detection/ &&  python3 extract-terms.py
	cd gender-bias-detection/eus/ && awk -f gen-regexes.awk > regex.tsv

run-tests:
	cd use-models-tools && python -m nose2
	cd serving/translate-batch/ && python -m nose2
	cd serving/translate-service/ && python -m nose2
