# Generates compositions/*.html and index.html from timeline.json + checks/example.json.
#   python3 -I tools/gen.py            (real timeline)
#   python3 -I tools/gen.py --fake     (estimate a timeline from SCRIPT.json at 2.9 words/s; layout tests only)
import json, os, re, sys

ROOT = os.getcwd()
EX = json.load(open("checks/example.json"))
SCRIPT = json.load(open("SCRIPT.json"))["scenes"]

if "--fake" in sys.argv:
    t, scenes, words = 0.0, [], []
    for n, s in enumerate(SCRIPT):
        ws = s["text"].split(); lead = 0.4 if n == 0 else 0.3
        for i, w in enumerate(ws):
            st = t + lead + i / 2.9
            words.append({"scene": s["id"], "i": i, "text": w, "start": round(st, 3), "end": round(st + 0.3, 3)})
        length = round(lead + len(ws) / 2.9 + 0.45 + (2.6 if n == len(SCRIPT) - 1 else 0), 2)
        scenes.append({"id": s["id"], "start": round(t, 2), "length": length, "voiceAt": lead, "voiceDur": 0})
        t += length
    T = {"total": round(t, 2), "scenes": scenes, "words": words}
else:
    T = json.load(open("timeline.json"))
SC = {s["id"]: s for s in T["scenes"]}
TOTAL = T["total"]
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

def w(sid, word, nth=0, edge="start"):
    """Absolute time of the nth occurrence of `word` in scene sid."""
    hits = [x for x in T["words"] if x["scene"] == sid and norm(x["text"]) == norm(word)]
    if len(hits) <= nth:
        raise SystemExit(f"anchor not found: {sid}/{word}#{nth}: {[x['text'] for x in T['words'] if x['scene'] == sid]}")
    return round(hits[nth][edge], 3)

def first(sid):
    return round([x for x in T["words"] if x["scene"] == sid][0]["start"], 3)

A = {
    "reset": round(SC["history"]["start"] + 0.05, 2),
    "hiPaint": w("history", "paint"), "hiPub": w("history", "published"), "hkSecret": w("hook", "secret"), "hkSpy": w("hook", "spy"),
    "mxStart": SC["mix"]["start"], "mxYellow": w("mix", "yellow"), "mxRed": w("mix", "red"), "mxBlue": w("mix", "blue"),
    "mxSwap": w("mix", "swap"),
    "maAdds": w("match", "add"), "maSame": w("match", "match"), "maKey": w("match", "key"),
    "spStart": SC["spy"]["start"], "spMix": w("spy", "mixes"), "spMud": w("spy", "wrong"), "spDouble": w("spy", "double"),
    "twStart": first("twist"), "twHard": w("twist", "hard"), "twDigits": w("twist", "600"), "twFast": w("twist", "fast"),
    "endStart": SC["end"]["start"], "enPad": w("end", "padlock"), "enSecret": w("end", "secret"), "enRoom": w("end", "room"),
}
# Camera: a few keys joined by a C1-continuous Hermite spline (velocity never jumps, never stops dead),
# sampled at 30 fps here so the world plays back exactly the path measured below.
FPS = 30
CAM_KEYS = [
    # t, position, look-at
    (0.0,                   [0.82, 5.67, 13.12],  [0.0, -0.5, -0.35]),
    (A["reset"] + 0.6,      [-0.46, 5.45, 12.39], [0.0, -0.45, -0.35]),
    (A["mxYellow"],         [0.0, 5.23, 11.88],   [0.0, -0.4, -0.4]),
    (A["mxRed"] + 0.3,      [-0.46, 5.14, 11.53],  [-0.1, -0.4, -0.3]),
    (A["mxBlue"] + 0.3,     [0.46, 5.14, 11.53],   [0.1, -0.4, -0.3]),
    (A["mxSwap"] + 1.1,     [0.0, 6.72, 12.57],    [0.0, -0.55, -0.35]),
    (A["maAdds"] + 0.4,     [-0.27, 5.32, 11.54],  [0.0, -0.4, -0.2]),
    (A["maKey"] - 0.5,      [0.18, 5.2, 10.99],   [0.0, -0.37, -0.2]),
    (A["spMix"] + 0.5,      [0.0, 5.6, 11.2],     [0.0, 0.45, -1.25]),
    (A["spMud"] - 0.2,      [0.05, 5.65, 11.1],   [0.0, 0.45, -1.25]),
    (A["spDouble"] + 0.4,   [0.0, 5.5, 11.3],     [0.0, 0.2, -0.9]),
    (A["twStart"] + 1.4,    [0.0, 5.7, 11.1],     [0.0, 0.5, -1.3]),
    (A["endStart"] - 0.4,   [0.08, 5.7, 11.0],    [0.0, 0.5, -1.3]),
    (A["endStart"] + 3.6,   [-0.55, 5.54, 12.39],   [0.0, -0.45, -0.35]),
    (TOTAL,                 [0.18, 5.74, 13.12],    [0.0, -0.47, -0.35]),
]
FOV_KEYS = [
    (0.0, 30.0), (A["maKey"] - 0.5, 30.0), (A["spMix"] + 0.5, 13.0), (A["spMud"] - 0.2, 12.5), (A["spDouble"] + 0.4, 19.0),
    (A["twStart"] + 1.4, 10.5), (A["endStart"] - 0.4, 10.0), (A["endStart"] + 3.6, 30.0), (TOTAL, 30.0),
]
MAX_SPEED, MAX_TURN = 4.8, 30.0   # 30-degree lens: the camera stands ~1.8x further back   # world units per second, degrees per second

def _hermite_path(keys, total, fps):
    ts = [k[0] for k in keys]
    def tangents(idx):
        out = []
        for i in range(len(keys)):
            j0, j1 = max(0, i - 1), min(len(keys) - 1, i + 1)
            scale = 0.5 if i in (0, len(keys) - 1) else 1.0
            out.append([(keys[j1][idx][d] - keys[j0][idx][d]) / (ts[j1] - ts[j0]) * scale for d in range(3)])
        return out
    tp, tl = tangents(1), tangents(2)
    frames = []
    for f in range(int(round(total * fps)) + 1):
        t = min(total, f / fps)
        k = 0
        while k < len(keys) - 2 and ts[k + 1] <= t:
            k += 1
        h = ts[k + 1] - ts[k]; u = 0 if h <= 0 else min(1, max(0, (t - ts[k]) / h))
        h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
        row = []
        for idx, tg in ((1, tp), (2, tl)):
            a, b = keys[k][idx], keys[k + 1][idx]
            row += [round(h00*a[d] + h10*h*tg[k][d] + h01*b[d] + h11*h*tg[k + 1][d], 4) for d in range(3)]
        frames.append(row)
    return frames

def _camera_report(path):
    import math
    wv = ww = tv = tw = 0
    for f in range(1, len(path)):
        p0, p1 = path[f - 1], path[f]
        v = math.dist(p0[:3], p1[:3]) * FPS
        d0 = [p0[3 + i] - p0[i] for i in range(3)]; d1 = [p1[3 + i] - p1[i] for i in range(3)]
        c = sum(a * b for a, b in zip(d0, d1)) / (math.hypot(*d0) * math.hypot(*d1))
        w = math.degrees(math.acos(max(-1, min(1, c)))) * FPS
        if v > wv: wv, tv = v, f / FPS
        if w > ww: ww, tw = w, f / FPS
    return wv, tv, ww, tw

CAM_PATH = _hermite_path(CAM_KEYS, TOTAL, FPS)
_fov = _hermite_path([(t, [f, 0, 0], [0, 0, 0]) for t, f in FOV_KEYS], TOTAL, FPS)
CAM_PATH = [row + [round(f[0], 3)] for row, f in zip(CAM_PATH, _fov)]   # 7th value: vertical FOV in degrees
_v, _tv, _w, _tw = _camera_report(CAM_PATH)
print(f"camera: max speed {_v:.2f} u/s at {_tv:.2f}s, max turn {_w:.1f} deg/s at {_tw:.2f}s")
if _v > MAX_SPEED or _w > MAX_TURN:
    raise SystemExit(f"camera too fast (limits {MAX_SPEED} u/s, {MAX_TURN} deg/s): give that move more time")
EVENTS = sorted([{"t": round(v, 2), "kind": k} for k, v in A.items()], key=lambda e: e["t"])
cfg = {"total": TOTAL, "anchors": A, "example": EX, "camPath": CAM_PATH, "fps": FPS, "events": EVENTS}
os.makedirs("compositions", exist_ok=True)
world = open("tools/world.template.html").read().replace("__CONFIG__", json.dumps(cfg)).replace("__DUR__", str(TOTAL))
open("compositions/world.html", "w").write(world)

# ------------------------------------------------------------------ HTML layers
AMBER, INK = "#F2A541", "#F4F1EA"
FONT_FACES = """
@font-face { font-family: 'InterV'; src: url('assets/fonts/Inter-700.woff2') format('woff2'); font-weight: 700; }
@font-face { font-family: 'InterV'; src: url('assets/fonts/Inter-400.woff2') format('woff2'); font-weight: 400; }
@font-face { font-family: 'MonoV'; src: url('assets/fonts/JetBrainsMono-400.woff2') format('woff2'); font-weight: 400; }
"""

def scene(cid, dur, css, body, js):
    return f"""<template>
  <style>
    {FONT_FACES}
    #root {{ position: absolute; inset: 0; overflow: hidden; background: transparent; font-family: 'InterV', Inter, sans-serif; color: {INK}; }}
    .mono {{ font-family: 'MonoV', 'JetBrains Mono', monospace; }}
    .shadow {{ text-shadow: 0 2px 18px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.6); }}
    {css}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="1080" data-height="1920" data-start="0" data-duration="{dur}">
    {body}
  </div>
  <script>
    (function () {{
    const tl = gsap.timeline({{ paused: true }});
    const D = {dur};
    {js}
    window.__timelines["{cid}"] = tl;
    }})();
  </script>
</template>
"""

def r(x, base):  # time relative to a layer's start
    return round(x - base, 2)

# hook title: on frame 0, fades as the history scene begins
def gen_hookui():
    s = SC["hook"]; dur = round(s["length"] + 0.4, 2)
    css = f"""
    #hk-title {{ position: absolute; left: 0; width: 1080px; top: 300px; text-align: center; font-size: 76px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.05; }}
    #hk-sub {{ position: absolute; left: 0; width: 1080px; top: 398px; text-align: center; font-size: 38px; font-weight: 400; color: rgba(244,241,234,0.8); }}
    #hk-sub b {{ color: {AMBER}; font-weight: 700; }}
    """
    body = """<div id="hk-title" class="shadow">A secret, out loud?</div>
    <div id="hk-sub" class="shadow">two pots match <b>·</b> the spy's doesn't</div>"""
    js = f'tl.to(["#hk-title", "#hk-sub"], {{opacity: 0, filter: "blur(6px)", duration: 0.35, ease: "power2.in"}}, {dur - 0.45:.2f});'
    return scene("hookui", dur, css, body, js), 0, dur

# history: year + paper title over the room
def gen_histui():
    s = SC["history"]; st = s["start"]; dur = s["length"]
    t_names = r(w("history", "Diffie") , st); t_pub = r(w("history", "published"), st)
    css = f"""
    #hi-year {{ position: absolute; left: 0; width: 1080px; top: 348px; text-align: center; font-size: 64px; font-weight: 700; letter-spacing: -0.015em; opacity: 0; }}
    #hi-year span {{ color: {AMBER}; }}
    #hi-full {{ position: absolute; left: 153px; width: 774px; top: 300px; text-align: center; font-size: 32px; color: rgba(244,241,234,0.75); opacity: 0; }}
    #hi-paper {{ position: absolute; left: 153px; width: 774px; top: 436px; text-align: center; font-size: 34px; font-weight: 400; font-style: italic; color: rgba(244,241,234,0.85); opacity: 0; }}
    #hi-merkle {{ position: absolute; left: 153px; width: 774px; top: 532px; text-align: center; font-size: 32px; color: rgba(244,241,234,0.7); opacity: 0; }}
    #hi-src {{ position: absolute; left: 153px; width: 774px; top: 486px; text-align: center; font-size: 32px; color: rgba(244,241,234,0.6); opacity: 0; }}
    """
    body = """<div id="hi-year" class="shadow">Diffie &amp; Hellman · <span>1976</span></div>
    <div id="hi-full" class="mono shadow">Whitfield Diffie &amp; Martin Hellman</div>
    <div id="hi-paper" class="shadow">“New Directions in Cryptography”</div>
    <div id="hi-src" class="mono shadow">IEEE Trans. Inf. Theory, Nov 1976</div>
    <div id="hi-merkle" class="mono shadow">Ralph Merkle: independent work</div>"""
    js = "\n    ".join([
        f'tl.fromTo("#hi-full", {{opacity: 0}}, {{opacity: 1, duration: 0.4}}, {max(0.05, t_names - 0.2):.2f});',
        f'tl.fromTo("#hi-year", {{opacity: 0, y: 14}}, {{opacity: 1, y: 0, duration: 0.45, ease: "power3.out"}}, {max(0.05, t_names - 0.3):.2f});',
        f'tl.fromTo(["#hi-paper", "#hi-src"], {{opacity: 0}}, {{opacity: 1, duration: 0.45, stagger: 0.12}}, {t_pub:.2f});',
        f'tl.fromTo("#hi-merkle", {{opacity: 0}}, {{opacity: 1, duration: 0.4}}, {t_pub + 0.7:.2f});',
        f'tl.to(["#hi-full", "#hi-year", "#hi-paper", "#hi-src", "#hi-merkle"], {{opacity: 0, filter: "blur(6px)", duration: 0.3, ease: "power2.in"}}, {dur - 0.3:.2f});',
    ])
    return scene("histui", dur, css, body, js), st, dur

# persistent honesty tag
def gen_tagui():
    dur = round(A["endStart"] + 0.6, 2)
    css = """#tg { position: absolute; left: 153px; width: 774px; top: 1640px; text-align: center; font-size: 32px; color: rgba(232,237,242,0.62); }"""
    body = '<div id="tg" class="mono shadow" data-layout-allow-safe-zone>illustrative: paint and toy numbers</div>'
    js = 'tl.to("#tg", {opacity: 0, duration: 0.5}, D - 0.5);'
    return scene("tagui", dur, css, body, js), 0, dur

# twist: the un-mixing counter, then a real 617-digit prime
def ffdhe2048_decimal():
    src = open("sources/03.md").read()
    blk = src.split("The hexadecimal representation of p is:")[1].split("The generator is")[0]
    hx = re.sub(r"[^0-9A-F]", "", blk)
    n = int(hx, 16)
    assert n.bit_length() == 2048
    d = str(n); assert len(d) == EX["digits2048"] == 617
    return d

def gen_twistui():
    s = SC["twist"]; st = s["start"]; dur = s["length"]
    t0 = r(A["twStart"], st) + 0.1; t_hard = r(A["twHard"], st); t_dig = r(A["twDigits"], st); t_fast = r(A["twFast"], st)
    tries = EX["tries"]
    step = max(0.3, min(0.55, (t_dig - 1.4 - t0) / (len(tries) - 1)))
    digits = ffdhe2048_decimal()
    rows = [digits[i:i + 36] for i in range(0, len(digits), 36)]
    css = f"""
    #tw-q {{ position: absolute; left: 0; width: 1080px; top: 300px; text-align: center; font-size: 50px; opacity: 0; }}
    #tw-q .x {{ color: {AMBER}; }}
    .tw-try {{ position: absolute; left: 340px; width: 400px; top: 386px; text-align: center; font-size: 40px; background: rgba(6,8,11,0.6); border-radius: 8px; padding: 2px 0; color: rgba(244,241,234,0.85); opacity: 0; }}
    .tw-try.hit {{ color: {AMBER}; }}
    #tw-wall {{ position: absolute; left: 153px; width: 774px; top: 530px; font-size: 21px; line-height: 1.24; color: rgba(244,241,234,0.78); text-align: center; opacity: 0; white-space: pre; }}
    #tw-wallbg {{ position: absolute; left: 213px; width: 654px; top: 470px; height: 540px; background: rgba(6,8,11,0.72); border-radius: 10px; opacity: 0; }}
    #tw-wlbl {{ position: absolute; left: 153px; width: 774px; top: 474px; text-align: center; font-size: 32px; color: {AMBER}; opacity: 0; }}
    #tw-run {{ position: absolute; left: 190px; width: 700px; top: 388px; text-align: center; font-size: 40px; color: rgba(244,241,234,0.9); background: rgba(6,8,11,0.6); border-radius: 8px; opacity: 0; }}
    #tw-no {{ position: absolute; left: 0; width: 1080px; top: 310px; text-align: center; font-size: 40px; color: rgba(244,241,234,0.9); opacity: 0; }}
    """
    try_html = "\n    ".join(
        f'<div id="tw-t{i}" class="tw-try mono shadow{" hit" if v == EX["A"] else ""}">x = {i + 1} → {v}{" ✓" if v == EX["A"] else ""}</div>' for i, v in enumerate(tries))
    body = f"""<div id="tw-q" class="mono shadow">{EX['g']}<sup class="x">x</sup> mod {EX['p']} = {EX['A']} → <span class="x">x = ?</span></div>
    {try_html}
    <div id="tw-wallbg"></div>
    <div id="tw-wlbl" class="mono">a real 2048-bit prime: 617 digits</div>
    <div id="tw-wall" class="mono">{chr(10).join(rows)}</div>
    <div id="tw-run" class="mono shadow">trying x = <span id="tw-n">1</span> …</div>
    <div id="tw-no" class="mono shadow">x = ? &nbsp;no known fast way</div>"""
    js = [f'tl.fromTo("#tw-q", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.3}}, {t0:.2f});']
    for i in range(len(tries)):
        a = t0 + 0.25 + i * step
        js.append(f'tl.fromTo("#tw-t{i}", {{opacity: 0}}, {{opacity: 1, duration: 0.06}}, {a:.2f});')
        if i < len(tries) - 1:
            js.append(f'tl.to("#tw-t{i}", {{opacity: 0, duration: 0.06}}, {a + step - 0.03:.2f});')
    last = t0 + 0.25 + (len(tries) - 1) * step
    js += [
        f'tl.to("#tw-t{len(tries) - 1}", {{opacity: 0, duration: 0.25}}, {max(last + 1.05, t_dig - 0.3):.2f});',
        f'tl.to("#tw-q", {{opacity: 0, duration: 0.25}}, {max(last + 0.6, t_dig - 0.45):.2f});',
        f'tl.fromTo(["#tw-wallbg", "#tw-wlbl"], {{opacity: 0}}, {{opacity: 1, duration: 0.35}}, {t_dig - 0.2:.2f});',
        f'tl.fromTo("#tw-wall", {{opacity: 0, clipPath: "inset(0 0 100% 0)"}}, {{opacity: 1, clipPath: "inset(0 0 0% 0)", duration: 1.1, ease: "power1.inOut"}}, {t_dig - 0.1:.2f});',
        f'tl.fromTo("#tw-no", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {t_fast - 0.3:.2f});',
        f'tl.fromTo("#tw-run", {{opacity: 0}}, {{opacity: 1, duration: 0.25}}, {t_dig - 0.1:.2f});',
        'const run = {v: 1};',
        f'tl.fromTo(run, {{v: 1}}, {{v: 9.7e11, duration: {round(dur - (t_dig - 0.1) - 0.3, 2)}, ease: "power3.in", onUpdate: () => {{ document.querySelector("#tw-n").textContent = Math.floor(run.v).toLocaleString("en-US"); }}}}, {t_dig - 0.1:.2f});',
        'tl.to(["#tw-wall", "#tw-wallbg", "#tw-wlbl", "#tw-no", "#tw-run"], {opacity: 0, filter: "blur(6px)", duration: 0.35, ease: "power2.in"}, D - 0.35);',
    ]
    return scene("twistui", dur, css, body, "\n    ".join(js)), st, dur

# the toy maths, centred at the top while the pots work
def gen_mathui():
    st = round(A["mxYellow"] - 0.7, 2); dur = round(A["twStart"] + 0.3 - st, 2); t_pubin = 0.1; t_pubout = r(A["mxSwap"] - 0.45, st)
    t_send = r(A["mxSwap"] - 0.2, st); t_fin = r(A["maAdds"] + 0.9, st); t_key = r(A["maKey"], st); t_spy = r(A["spMud"] - 0.2, st); t_ne = r(A["spDouble"] - 0.1, st); t_spy0 = r(A["spStart"], st)
    g, p = EX["g"], EX["p"]
    css = f"""
    .ml {{ position: absolute; left: 153px; width: 774px; text-align: center; font-size: 44px; opacity: 0; }}
    .ml .who {{ color: rgba(244,241,234,0.62); font-size: 36px; }}
    .ml {{ background: rgba(6,8,11,0.55); border-radius: 8px; }}
    #m0 {{ top: 300px; }} #m1 {{ top: 300px; }} #m2 {{ top: 366px; }} #m3 {{ top: 300px; color: {AMBER}; }} #m4 {{ top: 366px; color: {AMBER}; }}
    #m6 {{ top: 300px; }} #m7 {{ top: 372px; font-size: 64px; font-family: 'InterV', Inter, sans-serif; font-weight: 700; color: #e9dfae; }}
    #m5 {{ top: 444px; font-size: 54px; font-family: 'InterV', Inter, sans-serif; font-weight: 700; color: {AMBER}; }}
    """
    body = f"""<div id="m0" class="ml mono shadow" style="color:#F7DC6F">public: {g}, mod {p}</div>
    <div id="m1" class="ml mono shadow"><span class="who">Alice sends</span> {g}<sup>{EX['a']}</sup> mod {p} = {EX['A']}</div>
    <div id="m2" class="ml mono shadow"><span class="who">Bob sends</span> {g}<sup>{EX['b']}</sup> mod {p} = {EX['B']}</div>
    <div id="m3" class="ml mono shadow"><span class="who">Alice</span> {EX['B']}<sup>{EX['a']}</sup> mod {p} = {EX['shared']}</div>
    <div id="m4" class="ml mono shadow"><span class="who">Bob</span> {EX['A']}<sup>{EX['b']}</sup> mod {p} = {EX['shared']}</div>
    <div id="m5" class="ml shadow">key = {EX['shared']}</div>
    <div id="m6" class="ml mono shadow"><span class="who">spy</span> {EX['A']} × {EX['B']} mod {p} = {EX['eve']}</div>
    <div id="m7" class="ml shadow">{EX['eve']} ≠ {EX['shared']}</div>"""
    js = "\n    ".join([
        f'tl.fromTo("#m0", {{opacity: 0}}, {{opacity: 1, duration: 0.35}}, {t_pubin:.2f});',
        f'tl.to("#m0", {{opacity: 0, duration: 0.25}}, {t_pubout:.2f});',
        f'tl.fromTo(["#m1", "#m2"], {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.35, stagger: 0.15}}, {t_send:.2f});',
        f'tl.to(["#m1", "#m2"], {{opacity: 0, duration: 0.25}}, {t_fin - 0.3:.2f});',
        f'tl.fromTo(["#m3", "#m4"], {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.35, stagger: 0.15}}, {t_fin:.2f});',
        f'tl.fromTo("#m5", {{opacity: 0, scale: 0.9}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)"}}, {t_key - 0.1:.2f});',
        f'tl.to(["#m3", "#m4", "#m5"], {{opacity: 0, filter: "blur(6px)", duration: 0.3}}, {t_spy0 - 0.15:.2f});',
        f'tl.fromTo("#m6", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.35}}, {t_spy:.2f});',
        f'tl.fromTo("#m7", {{opacity: 0, scale: 0.9}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)"}}, {t_ne:.2f});',
        'tl.to(["#m6", "#m7"], {opacity: 0, filter: "blur(6px)", duration: 0.3}, D - 0.35);',
    ])
    return scene("mathui", dur, css, body, js), st, dur

# end: padlock + TLS 1.3
def gen_endui():
    s = SC["end"]; st = s["start"]; dur = s["length"]
    t_pad = r(A["enPad"], st)
    css = f"""
    #en-wrap {{ position: absolute; left: 0; width: 1080px; top: 272px; text-align: center; opacity: 0; }}
    #en-lock {{ width: 84px; height: 96px; display: block; margin: 0 auto 14px; }}
    #en-txt {{ font-size: 40px; line-height: 1.3; color: rgba(244,241,234,0.92); }}
    #en-txt span {{ color: {AMBER}; }}
    """
    body = f"""<div id="en-wrap" class="shadow">
      <svg id="en-lock" viewBox="0 0 84 96"><path d="M20 42 V28 a22 22 0 0 1 44 0 V42" fill="none" stroke="{AMBER}" stroke-width="8" stroke-linecap="round"/><rect x="8" y="42" width="68" height="50" rx="9" fill="{AMBER}"/><circle cx="42" cy="64" r="7" fill="#06080b"/><rect x="39" y="66" width="6" height="14" rx="3" fill="#06080b"/></svg>
      <div id="en-txt" class="mono">TLS 1.3<br/><span>elliptic-curve Diffie–Hellman</span></div>
    </div>"""
    js = f'tl.fromTo("#en-wrap", {{opacity: 0, y: 16}}, {{opacity: 1, y: 0, duration: 0.45, ease: "power3.out"}}, {max(t_pad - 0.15, r(A['endStart'] + 2.3, st)):.2f});'
    return scene("endui", dur, css, body, js), st, dur

# captions
def gen_captions():
    FIX = {"away.": "a way.", "color": "colour", "Unmixing": "Un-mixing", "600": "six hundred"}
    ws = [dict(x) for x in T["words"]]
    for x in ws:
        x["text"] = FIX.get(x["text"], x["text"])
    groups, cur = [], []
    for x in ws:
        if cur:
            prev = cur[-1]
            brk = (prev["scene"] != x["scene"] or (prev["text"][-1] in ",:" and len(cur) >= 2)
                   or x["start"] - prev["end"] >= 0.3 or len(cur) >= 5 or prev["text"][-1] in ".?!")
            if brk:
                groups.append(cur); cur = []
        cur.append(x)
    if cur: groups.append(cur)
    html, js = [], []
    for gi, g in enumerate(groups):
        g0 = round(max(0, g[0]["start"] - 0.12), 2)
        nxt = groups[gi + 1][0]["start"] - 0.12 if gi + 1 < len(groups) else TOTAL
        g1 = round(min(nxt, g[-1]["end"] + 0.5), 2)
        spans = " ".join(f'<span id="cap-{gi}-{k}" class="cw">{x["text"]}</span>' for k, x in enumerate(g))
        html.append(f'<div id="cap-g{gi}" class="clip capg" data-layout-allow-safe-zone data-start="{g0}" data-duration="{round(g1 - g0, 2)}" data-track-index="0"><div class="capin">{spans}</div></div>')
        for k, x in enumerate(g):
            js.append(f'tl.to("#cap-{gi}-{k}", {{color: "rgba(244,241,234,1)", duration: 0.08, ease: "none"}}, {round(x["start"], 2)});')
    css = """
    .capg { position: absolute; left: 210px; top: 1040px; width: 660px; text-align: center; }   /* inside every platform's clear band (y <= 1248) */
    .capin { display: inline-block; max-width: 660px; font-size: 48px; font-weight: 700; line-height: 1.22; letter-spacing: -0.005em; text-shadow: 0 2px 14px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.7); }
    .cw { color: rgba(244,241,234,0.55); }
    """
    out = f"""<template>
  <style>
    {FONT_FACES}
    #root {{ position: absolute; inset: 0; font-family: 'InterV', Inter, sans-serif; background: transparent; }}
    {css}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920" data-start="0" data-duration="{TOTAL}">
{chr(10).join('    ' + h for h in html)}
  </div>
  <script>
    (function () {{
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join('    ' + j for j in js)}
    window.__timelines["captions"] = tl;
    }})();
  </script>
</template>
"""
    return out, len(groups)

layers = []
for name, fn in [("hookui", gen_hookui), ("histui", gen_histui), ("tagui", gen_tagui), ("mathui", gen_mathui), ("twistui", gen_twistui), ("endui", gen_endui)]:
    html, st, dur = fn()
    open(f"compositions/{name}.html", "w").write(html)
    layers.append((name, round(st, 2), round(dur, 2)))
cap_html, ng = gen_captions()
open("compositions/captions.html", "w").write(cap_html)

hosts = [("world", 0, TOTAL, 1)] + [(n, s, d, 3 + k) for k, (n, s, d) in enumerate(layers)]
host_html = "\n".join(
    f'      <div id="{h}" data-composition-id="{h}" data-composition-src="compositions/{h}.html" data-start="{s}" data-duration="{d}" data-track-index="{n}" data-track-kind="graphics" data-width="1080" data-height="1920" style="z-index:{z}"></div>'
    for n, (h, s, d, z) in enumerate(hosts))
voice_html = "\n".join(
    f'      <audio id="vo-{s["id"]}" class="clip" src="assets/voice/{s["id"]}.wav" data-start="{round(s["start"] + s["voiceAt"], 2)}" data-duration="{s["voiceDur"]}" data-track-index="11" data-volume="1"></audio>'
    for s in T["scenes"] if os.path.exists(f"assets/voice/{s['id']}.wav"))
sfx = json.load(open("tmp/sfx_plan.json")) if os.path.exists("tmp/sfx_plan.json") else []
sfx_html = "\n".join(
    f'      <audio id="sfx-{n}" class="clip" src="{c["src"]}" data-start="{c["t"]}" data-duration="{c["dur"]}" data-track-index="{12 + n % 2}" data-volume="{c["vol"]}"></audio>'
    for n, c in enumerate(sfx))
music = json.load(open("tmp/music_plan.json")) if os.path.exists("tmp/music_plan.json") else None
music_html = (f'      <audio id="music-bed" class="clip" src="{music["src"]}" data-start="0" data-duration="{TOTAL}" data-track-index="14" data-volume="{music["vol"]}" data-fade-in="1.0" data-fade-out="{music.get("fadeOut", 6)}"></audio>' if music else "")

index = f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #06080b; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
{host_html}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{TOTAL}" data-track-index="10" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index:20"></div>
{voice_html}
{sfx_html}
{music_html}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
open("index.html", "w").write(index)
print("ok total", TOTAL, "captions", ng)
print(json.dumps(A))
