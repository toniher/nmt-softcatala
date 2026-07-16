MODELS_DIR ?= $(PWD)/models-data
MODELS_AINA_DIR ?= $(PWD)/models-data-aina

build-all: docker-build-use-models-tools docker-build-translate-service docker-build-translate-service-test docker-build-translate-batch

download-models:
	MODELS="$(MODELS)" MODELS_DIR="$(MODELS_DIR)" ./models/download-models.sh

download-aina-models:
	MODELS="$(MODELS)" MODELS_AINA_DIR="$(MODELS_AINA_DIR)" ./models/download-aina-models.sh

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
	docker compose up -d;

generate-bias-terms:
	cd gender-bias-detection/ &&  python3 extract-terms.py
	cd gender-bias-detection/eus/ && awk -f gen-regexes.awk > regex.tsv

run-tests:
	cd use-models-tools && python -m nose2
	cd serving/translate-batch/ && python -m nose2
	cd serving/translate-service/ && python -m nose2
