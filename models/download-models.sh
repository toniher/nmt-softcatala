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
# host needs only Docker (no wget/unzip). A pair already present is skipped when
# the Date: in its metadata/model_description.txt matches the manifest filename,
# and replaced otherwise. To update a model, change its date in models.list (see
# `make check-models`), re-run this script, and restart the services: they load
# the models at startup.

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
        # Even when a download fails: drop the staging dir and hand ownership back to the host user.
        trap "rm -rf .staging; chown -R \"\$HOST_UID:\$HOST_GID\" /srv/models" EXIT
        for f in $FILES; do
            pair="${f:0:7}"
            want="${f:8:10}"
            have="$(sed -n "s/^Date: *//p" "$pair/metadata/model_description.txt" 2>/dev/null | head -1)"
            if [ -d "$pair" ] && [ "$have" = "$want" ]; then
                echo "skip   $pair ($want, up to date)"
                continue
            fi
            if [ -d "$pair" ]; then
                echo "update $pair ${have:-unknown} -> $want"
            else
                echo "fetch  $f"
            fi
            # Unzip into a staging dir first: a failed download leaves the old model in place.
            rm -rf .staging && mkdir .staging
            wget -q -O ".staging/$f" "$URL/$f"
            unzip -q -o ".staging/$f" -d .staging -x "*/tensorflow/*"
            rm -rf ".old-$pair"
            [ -d "$pair" ] && mv "$pair" ".old-$pair"
            mv ".staging/$pair" "$pair"
            rm -rf ".old-$pair" .staging
        done
    '

echo "Done."
