#!/usr/bin/env python3
"""Generate one narration file per scene with Fish Audio.

Usage:
  FISH_API_KEY=... python3 fish_tts.py SCRIPT.json [--out tmp/tr] [--voice <reference_id>] [--speed 0.9]
  python3 fish_tts.py SCRIPT.json --key-file /path/to/key   # key read from a file, never echoed

SCRIPT.json is a list of {"id": "<scene id>", "text": "<what the narrator says>"}.
Writes <out>/<id>.wav for every scene. Raw files: run build_timeline.py next to normalise + time them.

Notes
- Model header defaults to "s2.1-pro-free" (usable without API credit at the time this skill was written).
  Paid models (e.g. "s1") return HTTP 402 when the account has no API credit.
- Default voice: Fish Audio "Documentary" (c3958f083c2d407982263c77cfa831e3). Search others:
  GET https://api.fish.audio/model?title=narrator&language=en&sort_by=score
- Fish voices read fast (~3.4 words/s); prosody speed 0.9 gives a documentary pace.
"""
import argparse, json, os, sys, urllib.request, urllib.error

ap = argparse.ArgumentParser()
ap.add_argument("script")
ap.add_argument("--out", default="tmp/tr")
ap.add_argument("--voice", default="c3958f083c2d407982263c77cfa831e3")
ap.add_argument("--model", default="s2.1-pro-free")
ap.add_argument("--speed", type=float, default=0.9)
ap.add_argument("--key-file")
ap.add_argument("--only", help="comma-separated scene ids to (re)generate")
a = ap.parse_args()

key = open(a.key_file).read().strip() if a.key_file else os.environ.get("FISH_API_KEY", "").strip()
if not key:
    sys.exit("Set FISH_API_KEY or pass --key-file")
os.makedirs(a.out, exist_ok=True)
only = set(a.only.split(",")) if a.only else None

for scene in json.load(open(a.script)):
    if only and scene["id"] not in only:
        continue
    body = json.dumps({"text": scene["text"], "reference_id": a.voice, "format": "wav",
                       "normalize": True, "prosody": {"speed": a.speed}}).encode()
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "model": a.model})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"{scene['id']}: HTTP {e.code} {e.read()[:300]!r}")
    path = os.path.join(a.out, scene["id"] + ".wav")
    open(path, "wb").write(data)
    print(f"{scene['id']}: {len(data)} bytes -> {path}")
