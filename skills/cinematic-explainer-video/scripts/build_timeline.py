#!/usr/bin/env python3
"""Transcribe, normalise and lay out the narration. Run from the HyperFrames project root.

Input : SCRIPT.json (scene order) and tmp/tr/<id>.wav (raw TTS, e.g. from fish_tts.py)
Output: assets/voice/<id>.wav  (loudnorm -16 LUFS, -1.5 dBTP, 48 kHz)
        tmp/tr/<id>.json        (word timings from `npx hyperframes transcribe`)
        timeline.json           ({total, scenes:[{id,start,length,voiceAt,voiceDur}], words:[{scene,i,text,start,end}]})

Scene length = lead silence + last word end + tail; the last scene also holds END_HOLD seconds.
Word times in timeline.json are absolute (film) seconds. Print per-scene indices with word_index.py
before wiring animation anchors to words.

Transcript checks (warnings only, printed at the end; thresholds.json keys ttsLoopRepeats, transcriptWerMax):
- TTS loop: any 1-3-word phrase repeated 3+ times in a row in a scene transcript. Rewrite the line; don't re-roll.
- Script vs transcript word error rate per scene (case, punctuation and number spelling normalised, so
  "one hundred percent" == "100%"). A high WER means a dropped/invented word: captions and anchors will drift.
  python3 build_timeline.py --check-only   # run only these checks on existing tmp/tr/*.json; writes nothing
"""
import json, os, re, shutil, subprocess, sys

LEAD = {}            # per-scene lead silence override, e.g. {"hook": 0.4}
DEFAULT_LEAD, TAIL, END_HOLD = 0.35, 0.5, 2.6
FIRST_LEAD = 0.4
MODEL = os.environ.get("TRANSCRIBE_MODEL", "small.en")
HERE = os.path.dirname(os.path.abspath(__file__))

def _thresholds():
    try:
        with open(os.path.join(HERE, "thresholds.json")) as fh:
            th = json.load(fh)
        return th["ttsLoopRepeats"]["value"], th["transcriptWerMax"]["value"]
    except (OSError, KeyError, ValueError):
        return 3, 0.05

LOOP_REPEATS, WER_MAX = _thresholds()

def _canonical():
    """check_facts.canonical_words (number-aware) when it sits next to this file; plain words otherwise."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_facts", os.path.join(HERE, "check_facts.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.canonical_words
    except Exception:
        return lambda s: re.findall(r"[a-z0-9']+", s.lower().replace("’", "'").replace("-", " "))

canon = _canonical()

def loops(words, repeats=LOOP_REPEATS):
    """[(phrase, count, index)] for 1-3-word n-grams repeated `repeats`+ times in a row."""
    w = [re.sub(r"[^\w']", "", x.lower()) for x in words]
    found, i = [], 0
    while i < len(w):
        best = None
        for n in (1, 2, 3):
            k = 1
            while i + (k + 1) * n <= len(w) and w[i + k * n:i + (k + 1) * n] == w[i:i + n]:
                k += 1
            if k >= repeats and w[i] and (best is None or k * n > best[1] * len(best[0].split())):
                best = (" ".join(w[i:i + n]), k)
        if best:
            found.append((best[0], best[1], i))
            i += best[1] * len(best[0].split())
        else:
            i += 1
    return found

def wer(ref, hyp):
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)

def transcript_warnings(sid, text, tw):
    out = []
    for phrase, k, i in loops([x["text"] for x in tw]):
        out.append(f"{sid}: TTS loop, \"{phrase}\" x{k} at word {i} (t={tw[i]['start']:.2f}s). Rewrite the line.")
    ref, hyp = canon(text), canon(" ".join(x["text"] for x in tw))
    e = wer(ref, hyp)
    if e > WER_MAX:
        out.append(f"{sid}: transcript differs from script, WER {e:.0%} (max {WER_MAX:.0%})\n"
                   f"      script:     {' '.join(ref)}\n      transcript: {' '.join(hyp)}")
    return out

def load_scenes(path="SCRIPT.json"):
    data = json.load(open(path))
    return data["scenes"] if isinstance(data, dict) else data      # {"mode":..., "scenes": [...]} or [...]

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

def load_words(tj):
    tr = json.load(open(tj))
    return tr if isinstance(tr, list) else tr["words"]

def main():
    scenes_in = load_scenes()
    warnings = []
    if "--check-only" in sys.argv:
        for sc in scenes_in:
            tj = f"tmp/tr/{sc['id']}.json"
            if not os.path.exists(tj):
                warnings.append(f"{sc['id']}: no transcript {tj}")
                continue
            warnings += transcript_warnings(sc["id"], sc["text"], load_words(tj))
        report(warnings, len(scenes_in))
        return
    ids = [s["id"] for s in scenes_in]
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
        tw = load_words(tj)
        warnings += transcript_warnings(sid, scenes_in[n]["text"], tw)
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
    report(warnings, len(ids))

def report(warnings, n):
    if warnings:
        print(f"\nWARN  transcript checks ({len(warnings)}):")
        for w in warnings:
            print("  " + w)
        print("  A stale tmp/tr/<id>.json is reused: delete it after regenerating that scene's audio.")
    else:
        print(f"transcript checks: {n} scenes, no TTS loops, WER <= {WER_MAX:.0%} everywhere")

if __name__ == "__main__":
    main()
