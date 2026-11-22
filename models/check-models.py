#!/usr/bin/env python3
#
# Compares the model manifests with what is published and what is installed.
# Run it with `make check-models`; it changes nothing.
#
#   Softcatalà: models.list dates vs the newest zip per pair in the published
#               index (MODELS_URL) vs Date: in <pair>/metadata/model_description.txt
#   AINA:       the four files used from each HuggingFace repo (at the pinned
#               commit or main) vs the Fingerprint: written by download-aina-models.sh
#
# Standard library only, so it runs in a plain python container.

import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("MODELS_URL", "https://www.softcatala.org/pub/softcatala/opennmt/models/2022-11-22")
MODELS_DIR = os.environ.get("MODELS_DIR", "models-data")
MODELS_AINA_DIR = os.environ.get("MODELS_AINA_DIR", "models-data-aina")
AINA_FILES = ["config.json", "model.bin", "shared_vocabulary.json", "spm.model"]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "nmt-softcatala check-models"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def manifest(name, entry):
    """Yields (fields, active) for each line matching the entry regex; commented-out ones are inactive."""
    with open(os.path.join(HERE, name)) as f:
        for line in f:
            text = line.strip().lstrip("#").strip()
            if re.fullmatch(entry, text):
                yield text.split(), not line.lstrip().startswith("#")


def metadata(models_dir, pair, key):
    try:
        with open(os.path.join(models_dir, pair, "metadata", "model_description.txt")) as f:
            match = re.search(rf"^{key}: *(\S+)", f.read(), re.M)
    except FileNotFoundError:
        return "-"
    return match.group(1) if match else "?"


def table(rows):
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]) - 1)]
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) + "  " + row[-1])


def check_softcatala():
    print(f"Softcatalà models ({URL})\n")
    published = {}
    for pair, date in re.findall(r'href="(\w{3}-\w{3})-(\d{4}-\d{2}-\d{2})\.zip"', fetch(URL + "/")):
        published[pair] = max(date, published.get(pair, date))

    rows = [("pair", "manifest", "published", "installed", "note")]
    listed = set()
    for (zipname, *_), active in manifest("models.list", r"\w{3}-\w{3}-\d{4}-\d{2}-\d{2}\.zip"):
        pair, date = zipname[:7], zipname[8:18]
        listed.add(pair)
        latest = published.get(pair, "-")
        have = metadata(MODELS_DIR, pair, "Date")
        notes = []
        if not active:
            notes.append("excluded")
        if latest > date:
            notes.append(f"newer published: {pair}-{latest}.zip")
        if active and have == "-":
            notes.append("not downloaded")
        elif active and have != date:
            notes.append("installed differs (run make download-models)")
        rows.append((pair, date, latest, have, ", ".join(notes) or "ok"))
    for pair in sorted(set(published) - listed):
        rows.append((pair, "-", published[pair], metadata(MODELS_DIR, pair, "Date"), "not in manifest"))
    table(rows)


def aina_fingerprint(repo, revision):
    info = json.loads(fetch(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true"))
    blobs = {s["rfilename"]: s["blobId"] for s in info["siblings"]}
    return hashlib.sha1(" ".join(blobs[f] for f in AINA_FILES).encode()).hexdigest()[:12]


def check_aina():
    print("\nAINA models (HuggingFace)\n")
    rows = [("pair", "repo", "revision", "remote", "installed", "note")]
    for (repo, pair, *rest), active in manifest("aina-models.list", r"\S+/\S+ +\w{3}-\w{3}( +\w+)?"):
        revision = rest[0] if rest else "main"
        if not active:
            rows.append((pair, repo, revision[:12], "-", metadata(MODELS_AINA_DIR, pair, "Fingerprint"), "excluded"))
            continue
        try:
            remote = aina_fingerprint(repo, revision)
        except Exception as e:
            rows.append((pair, repo, revision[:12], "?", metadata(MODELS_AINA_DIR, pair, "Fingerprint"), f"error: {e}"))
            continue
        have = metadata(MODELS_AINA_DIR, pair, "Fingerprint")
        notes = []
        if have == "-":
            notes.append("not downloaded")
        elif have == "?":
            notes.append("downloaded before fingerprints (run make download-aina-models once)")
        elif have != remote:
            notes.append("model files changed (run make download-aina-models)")
        if rest and aina_fingerprint(repo, "main") != remote:
            notes.append("newer on main")
        rows.append((pair, repo, revision[:12], remote, have, ", ".join(notes) or "ok"))
    table(rows)


if __name__ == "__main__":
    check_softcatala()
    check_aina()
    sys.exit(0)
