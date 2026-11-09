#!/usr/bin/env python3
"""Print every word with its index and time, per scene, from timeline.json.

Use this BEFORE you wire an animation anchor to a word ("the threads draw on 'thread.'").
Counting words by eye is the most common bug in this pipeline: 'a', 'the' and split numbers
shift every index after them.

  python3 word_index.py            # times relative to each scene's start
  python3 word_index.py --abs      # absolute film time
"""
import json, sys
T = json.load(open("timeline.json"))
st = {s["id"]: s["start"] for s in T["scenes"]}
absolute = "--abs" in sys.argv
cur = None
for w in T["words"]:
    if w["scene"] != cur:
        cur = w["scene"]; print(f"\n## {cur}  (scene start {st[cur]:.2f}s)")
    tt = w["start"] if absolute else w["start"] - st[cur]
    print(f"  [{w['i']:2d}] {w['text']:<14s} {tt:6.2f}")
