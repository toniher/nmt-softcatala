#!/usr/bin/env bash
#
# Downloads AINA (Projecte Aina / BSC) NMT models from HuggingFace into a local
# directory so they can be bind-mounted into the translation containers at
# runtime (no data image), alongside the Softcatalà models.
#
# AINA models are already CTranslate2 + SentencePiece, so they are normalized
# into the same on-disk layout the Softcatalà models use and loaded by the same
# nmt_sc.ctranslate.CTranslate class:
#     <pair>/ctranslate2/{config.json,model.bin,shared_vocabulary.json}
#     <pair>/tokenizer/sp_m.model
#     <pair>/metadata/model_description.txt   (generated here)
#
# The set of models comes from models/aina-models.list. Override or subset with:
#   MODELS="eng-cat cat-eng"          space-separated pairs to download
#   MODELS_AINA_DIR=/path/to/models   where to extract (default: ./models-data-aina)
#
# Downloading and normalization run inside a throwaway python container, so the
# host needs only Docker. Already-present pairs are skipped.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="$HERE/aina-models.list"

DIR="${MODELS_AINA_DIR:-$PWD/models-data-aina}"
FILTER="${MODELS:-}"

if [ ! -f "$MANIFEST" ]; then
    echo "Manifest not found: $MANIFEST" >&2
    exit 1
fi

# Build the "repo_id pair" list from the manifest, optionally filtered by pair.
# Entries are newline-separated so repo id and pair stay paired.
entries=""
while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                 # strip comments
    line="$(echo "$line" | xargs)"     # trim/collapse whitespace
    [ -z "$line" ] && continue
    pair="$(echo "$line" | awk '{print $2}')"
    if [ -n "$FILTER" ]; then
        case " $FILTER " in
            *" $pair "*) ;;
            *) continue ;;
        esac
    fi
    entries="$entries$line"$'\n'
done < "$MANIFEST"

entries="$(printf '%s' "$entries" | sed '/^$/d')"
if [ -z "$entries" ]; then
    echo "No models selected (manifest empty or MODELS filter matched nothing)." >&2
    exit 1
fi

mkdir -p "$DIR"
echo "Downloading AINA models into: $DIR"
echo "Models:"
echo "$entries" | sed 's/^/  /'

docker run --rm \
    -v "$DIR:/srv/models" \
    -e ENTRIES="$entries" \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    python:3.12-slim bash -c '
        set -e
        pip install --quiet --no-cache-dir huggingface_hub >/dev/null
        cd /srv/models
        printf "%s\n" "$ENTRIES" | while read -r repo pair; do
            [ -z "$repo" ] && continue
            if [ -d "$pair" ]; then
                echo "skip  $pair (already present)"
                continue
            fi
            echo "fetch $repo -> $pair"
            tmp="/tmp/$pair"
            rm -rf "$tmp"
            python - "$repo" "$tmp" <<"PY"
import sys
from huggingface_hub import snapshot_download
repo, dest = sys.argv[1], sys.argv[2]
snapshot_download(
    repo_id=repo,
    local_dir=dest,
    allow_patterns=["config.json", "model.bin", "shared_vocabulary.json", "spm.model"],
)
PY
            mkdir -p "$pair/ctranslate2" "$pair/tokenizer" "$pair/metadata"
            mv "$tmp/config.json" "$tmp/model.bin" "$tmp/shared_vocabulary.json" "$pair/ctranslate2/"
            mv "$tmp/spm.model" "$pair/tokenizer/sp_m.model"
            echo "AINA $repo (BSC / Projecte Aina)" > "$pair/metadata/model_description.txt"
            rm -rf "$tmp"
        done
        # Hand ownership back to the host user so files stay manageable.
        chown -R "$HOST_UID:$HOST_GID" /srv/models
    '

echo "Done."
