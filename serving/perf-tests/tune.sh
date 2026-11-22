#!/bin/bash
# Benchmarks translate-service thread layouts on this host. See serving/TUNING.md.
#
#   serving/perf-tests/tune.sh [WORKERS:THREADS:INTER:INTRA ...]
#   e.g. serving/perf-tests/tune.sh 2:4:1:6 2:4:3:2 1:8:4:3 1:8:6:2
#
# Needs only Docker, the translate-service image (make docker-build-translate-service)
# and the eng-cat model in MODELS_DIR. Settings (environment variables):
#   MODELS_DIR   models directory               (default: ./models-data)
#   CPUSET       CPUs for the service, e.g. 0-5  (default: all; pin it to emulate a smaller host)
#   WRK_CPUSET   CPUs for the load generator     (default: all; keep it off CPUSET when pinning)
#   DURATION     length of each run              (default: 15s)
#   CONCURRENCY  concurrent connections to test  (default: "1 4 8 16")
#   PAYLOADS     load files: short and/or para   (default: "short para")
#   BEAM_SIZE    CTRANSLATE_BEAM_SIZE            (default: 2, as in compose.yml)
#   PORT         host port used for the service (default: 8790)
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
MODELS_DIR=$(realpath "${MODELS_DIR:-$HERE/../../models-data}")
DURATION=${DURATION:-15s}
CONCURRENCY=${CONCURRENCY:-1 4 8 16}
PAYLOADS=${PAYLOADS:-short para}
BEAM_SIZE=${BEAM_SIZE:-2}
PORT=${PORT:-8790}
CONFIGS=${*:-2:4:1:6 2:4:3:2 1:8:4:3 1:8:6:2}
NAME=translate-service-tune

[ -d "$MODELS_DIR/eng-cat" ] || { echo "No eng-cat model in $MODELS_DIR (make download-models MODELS=eng-cat)"; exit 1; }

docker build -q -t wrk-local - >/dev/null <<'DOCKERFILE'
FROM alpine:3.22
RUN apk add --no-cache wrk
ENTRYPOINT ["wrk"]
DOCKERFILE

trap 'docker stop $NAME >/dev/null 2>&1 || true' EXIT
WRK="docker run --rm --network host ${WRK_CPUSET:+--cpuset-cpus $WRK_CPUSET} -v $HERE:/s:ro wrk-local"

echo "host: $(nproc) CPUs; service CPUs: ${CPUSET:-all}; beam size: $BEAM_SIZE; $DURATION per run"
printf "%-10s %-6s %5s %8s %9s %9s %6s\n" "W:T:I:X" load conns "req/s" "p50 ms" "p99 ms" errors
for config in $CONFIGS; do
    IFS=: read -r workers threads inter intra <<< "$config"
    docker run -d --rm --name $NAME ${CPUSET:+--cpuset-cpus $CPUSET} -p $PORT:8700 \
        -v "$MODELS_DIR":/srv/models:ro \
        -e GUNICORN_WORKERS=$workers -e GUNICORN_THREADS=$threads \
        -e CTRANSLATE_INTER_THREADS=$inter -e CTRANSLATE_INTRA_THREADS=$intra -e CTRANSLATE_BEAM_SIZE=$BEAM_SIZE \
        translate-service >/dev/null
    until curl -sf "localhost:$PORT/listPairs" >/dev/null; do sleep 1; done
    $WRK -t2 -c4 -d5s -s /s/para.lua "http://localhost:$PORT/translate/" >/dev/null  # warm-up

    for payload in $PAYLOADS; do
        for conns in $CONCURRENCY; do
            read -r _ rps p50 p99 errors < <($WRK -t$(( conns < 2 ? 1 : 2 )) -c$conns -d$DURATION --timeout 30s \
                -s /s/$payload.lua "http://localhost:$PORT/translate/" | grep '^RESULT')
            printf "%-10s %-6s %5s %8s %9s %9s %6s\n" "$config" $payload $conns $rps $p50 $p99 $errors
        done
    done
    echo "$config memory: $(docker stats --no-stream --format '{{.MemUsage}}' $NAME | cut -d/ -f1)"
    docker stop $NAME >/dev/null
done
