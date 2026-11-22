#!/bin/bash
UPLOAD_FOLDER=/srv/data/files/
mkdir -p $UPLOAD_FOLDER

# Process/thread layout; see serving/TUNING.md. Each worker loads every model.
# Request threads mostly wait on CTranslate2 (which releases the GIL), so threads, not
# processes, provide the request concurrency.
WORKERS=${GUNICORN_WORKERS:-2}
THREADS=${GUNICORN_THREADS:-4}

exec gunicorn --limit-request-line 8192 --workers=$WORKERS --threads=$THREADS \
     --graceful-timeout 90 --timeout 90 translate-service:app -b 0.0.0.0:8700
