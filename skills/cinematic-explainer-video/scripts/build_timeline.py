#!/usr/bin/env python3
"""Transcribe, normalise and lay out the narration. Run from the HyperFrames project root.

Input : SCRIPT.json (scene order) and tmp/tr/<id>.wav (raw TTS, e.g. from fish_tts.py)
Output: assets/voice/<id>.wav  (loudnorm -16 LUFS, -1.5 dBTP, 48 kHz)
        tmp/tr/<id>.json        (word timings from `npx hyperframes transcribe`)
        timeline.json           ({total, scenes:[{id,start,length,voiceAt,voiceDur}], words:[{scene,i,text,start,end}]})

Scene length = lead silence + last word end + tail; the last scene also holds END_HOLD seconds.
Word times in timeline.json are absolute (film) seconds. Print per-scene indices with word_index.py
before wiring animation anchors to words.
"""
import json, os, shutil, subprocess, sys

LEAD = {}            # per-scene lead silence override, e.g. {"hook": 0.4}
DEFAULT_LEAD, TAIL, END_HOLD = 0.35, 0.5, 2.6
FIRST_LEAD = 0.4
MODEL = os.environ.get("TRANSCRIBE_MODEL", "small.en")

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

ids = [s["id"] for s in json.load(open("SCRIPT.json"))]
os.makedirs("assets/voice", exist_ok=True)
t, scenes, words = 0.0, [], []
for n, sid in enumerate(ids):
    raw = f"tmp/tr/{sid}.wav"
    if not os.path.exists(raw):
        sys.exit(f"missing {raw}")
    tj = f"tmp/tr/{sid}.json"
    if not os.path.exists(tj):
        # transcribe writes transcript.json next to the input file
        subprocess.run(["npx", "hyperframes", "transcribe", raw, "--model", MODEL, "--json"], check=True, stdout=subprocess.DEVNULL)
        shutil.move("tmp/tr/transcript.json", tj)
    tr = json.load(open(tj)); tw = tr if isinstance(tr, list) else tr["words"]
    out = f"assets/voice/{sid}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", out], check=True)
    lead = LEAD.get(sid, FIRST_LEAD if n == 0 else DEFAULT_LEAD)
    length = round(lead + tw[-1]["end"] + TAIL + (END_HOLD if n == len(ids) - 1 else 0), 2)
    scenes.append({"id": sid, "start": round(t, 2), "length": length, "voiceAt": lead, "voiceDur": round(dur(out), 2)})
    for i, w in enumerate(tw):
        words.append({"scene": sid, "i": i, "text": w["text"], "start": round(t + lead + w["start"], 3), "end": round(t + lead + w["end"], 3)})
    print(f"{sid:10s} start {t:6.2f}  len {length:5.2f}  | {' '.join(w['text'] for w in tw)}")
    t += length
json.dump({"total": round(t, 2), "scenes": scenes, "words": words}, open("timeline.json", "w"), indent=1)
print("total", round(t, 2), "s -> timeline.json")
