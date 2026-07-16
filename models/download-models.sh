#!/usr/bin/env bash
#
# Downloads Softcatalà NMT models into a local directory so they can be
# bind-mounted into the translation containers at runtime (no data image).
#
# The set of models comes from models/models.list. Override or subset it with:
#   MODELS="eng-cat cat-eng"      space-separated pair prefixes to download
#   MODELS_DIR=/path/to/models    where to extract (default: ./models-data)
#   MODELS_URL=https://...        base download URL
#
# Downloading and unzipping run inside a throwaway Debian container, so the
# host needs only Docker (no wget/unzip). Already-present pairs are skipped.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="$HERE/models.list"

URL="${MODELS_URL:-https://www.softcatala.org/pub/softcatala/opennmt/models/2022-11-22}"
DIR="${MODELS_DIR:-$PWD/models-data}"
FILTER="${MODELS:-}"

if [ ! -f "$MANIFEST" ]; then
    echo "Manifest not found: $MANIFEST" >&2
    exit 1
fi

# Build the list of zip files from the manifest, optionally filtered by pair.
files=""
while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                 # strip comments
    line="$(echo "$line" | xargs)"     # trim whitespace
    [ -z "$line" ] && continue
    if [ -n "$FILTER" ]; then
        pair="${line:0:7}"
        case " $FILTER " in
            *" $pair "*) ;;
            *) continue ;;
        esac
    fi
    files="$files $line"
done < "$MANIFEST"

files="$(echo "$files" | xargs)"
if [ -z "$files" ]; then
    echo "No models selected (manifest empty or MODELS filter matched nothing)." >&2
    exit 1
fi

mkdir -p "$DIR"
echo "Downloading into: $DIR"
echo "Models: $files"

docker run --rm \
    -v "$DIR:/srv/models" \
    -e URL="$URL" \
    -e FILES="$files" \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    debian:bookworm-slim bash -c '
        set -e
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends wget unzip ca-certificates >/dev/null
        cd /srv/models
        for f in $FILES; do
            pair="${f:0:7}"
            if [ -d "$pair" ]; then
                echo "skip  $pair (already present)"
                continue
            fi
            echo "fetch $f"
            wget -q "$URL/$f"
            unzip -q -o "$f" -x "*/tensorflow/*"
            rm -f "$f"
        done
        # Hand ownership back to the host user so files stay manageable.
        chown -R "$HOST_UID:$HOST_GID" /srv/models
    '

echo "Done."
