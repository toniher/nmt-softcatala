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
# host needs only Docker.
#
# A manifest line may pin a HuggingFace commit as a third column; otherwise the
# latest (main) is used. The model version is a fingerprint of the four files
# used (README-only commits do not change it), stored with the commit in
# metadata/model_description.txt. A pair already present is skipped when its
# fingerprint matches the remote one, and replaced otherwise. Restart the
# services afterwards: they load the models at startup.

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
        pip install --quiet --no-cache-dir --root-user-action=ignore --disable-pip-version-check huggingface_hub >/dev/null
        cd /srv/models
        # Even when a download fails: drop the staging dir and hand ownership back to the host user.
        trap "rm -rf .staging; chown -R \"\$HOST_UID:\$HOST_GID\" /srv/models" EXIT
        python - <<"PY"
import hashlib, os, re, shutil
from huggingface_hub import HfApi, snapshot_download

FILES = ["config.json", "model.bin", "shared_vocabulary.json", "spm.model"]
api = HfApi()

def installed(pair):
    try:
        with open(f"{pair}/metadata/model_description.txt") as f:
            m = re.search(r"^Fingerprint: *(\S+)", f.read(), re.M)
            return m.group(1) if m else None
    except FileNotFoundError:
        return None

for line in os.environ["ENTRIES"].splitlines():
    repo, pair, *rest = line.split()
    revision = rest[0] if rest else "main"
    try:
        # The version is the four files we use; README-only commits do not count.
        info = api.model_info(repo, revision=revision, files_metadata=True)
    except Exception as e:
        if os.path.isdir(pair):
            print(f"warn   {pair}: cannot reach {repo} ({e}); keeping installed model")
            continue
        raise
    blobs = {s.rfilename: s.blob_id for s in info.siblings}
    fingerprint = hashlib.sha1(" ".join(blobs[f] for f in FILES).encode()).hexdigest()[:12]
    have = installed(pair)
    if os.path.isdir(pair) and have == fingerprint:
        print(f"skip   {pair} ({fingerprint}, up to date)")
        continue
    old = have or "unknown"
    print(f"update {pair} {old} -> {fingerprint}" if os.path.isdir(pair)
          else f"fetch  {repo}@{revision} -> {pair}")
    # Build the new model in a staging dir: a failed download leaves the old one in place.
    tmp, stage = f"/tmp/{pair}", ".staging"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(stage, ignore_errors=True)
    snapshot_download(repo_id=repo, revision=info.sha, local_dir=tmp, allow_patterns=FILES)
    for d in ("ctranslate2", "tokenizer", "metadata"):
        os.makedirs(f"{stage}/{d}")
    for f in FILES[:3]:
        shutil.move(f"{tmp}/{f}", f"{stage}/ctranslate2/{f}")
    shutil.move(f"{tmp}/spm.model", f"{stage}/tokenizer/sp_m.model")
    with open(f"{stage}/metadata/model_description.txt", "w") as f:
        f.write(f"AINA {repo} (BSC / Projecte Aina)\nRevision: {info.sha}\nFingerprint: {fingerprint}\n")
    shutil.rmtree(tmp)
    shutil.rmtree(f".old-{pair}", ignore_errors=True)
    if os.path.isdir(pair):
        os.rename(pair, f".old-{pair}")
    os.rename(stage, pair)
    shutil.rmtree(f".old-{pair}", ignore_errors=True)
PY
    '

echo "Done."
