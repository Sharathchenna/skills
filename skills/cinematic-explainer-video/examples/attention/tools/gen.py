# Generates index.html and compositions/*.html from timeline.json.
# Word positions are computed here from Inter 700 metrics so every thread meets its word exactly.
import json, math, os

T = json.load(open("timeline.json"))
SC = {s["id"]: s for s in T["scenes"]}
W = json.load(open("tmp/inter700_widths.json"))
os.makedirs("compositions", exist_ok=True)

AMBER = "#F2A541"
INK = "#F4F1EA"
WORDS = ["The", "animal", "didn’t", "cross", "the", "street", "because", "it", "was", "too", "tired."]
LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10]]
IT, ANIMAL, STREET, TIRED = 7, 1, 5, 10
# Illustrative attention weights of "it" over the sentence (sum = 1.00)
W_TIRED = [0.03, 0.55, 0.02, 0.03, 0.02, 0.15, 0.02, 0.08, 0.02, 0.01, 0.07]
W_WIDE  = [0.02, 0.14, 0.02, 0.04, 0.03, 0.52, 0.02, 0.09, 0.01, 0.01, 0.10]
assert abs(sum(W_TIRED) - 1) < 1e-9 and abs(sum(W_WIDE) - 1) < 1e-9

FONT_FACES = """
@font-face { font-family: 'InterV'; src: url('assets/fonts/Inter-700.woff2') format('woff2'); font-weight: 700; }
@font-face { font-family: 'InterV'; src: url('assets/fonts/Inter-400.woff2') format('woff2'); font-weight: 400; }
@font-face { font-family: 'MonoV'; src: url('assets/fonts/JetBrainsMono-400.woff2') format('woff2'); font-weight: 400; }
"""

def text_w(s, fs):
    return sum(W.get(c, 0.6) for c in s) * fs

def layout(fs, top, lh, cx=540, gap_em=0.30):
    """Centre x/y and width for every word."""
    pos = [None] * len(WORDS)
    for li, line in enumerate(LINES):
        ws = [text_w(WORDS[i], fs) for i in line]
        gap = gap_em * fs
        total = sum(ws) + gap * (len(line) - 1)
        x = cx - total / 2
        for i, w in zip(line, ws):
            pos[i] = {"x": round(x + w / 2, 1), "y": top + li * lh, "w": round(w, 1), "line": li}
            x += w + gap
    return pos

def arc(p, q, fs, lift=1.0):
    """Quadratic arc from word p to word q (dicts with x, y)."""
    h = fs * 0.40
    if p["line"] == q["line"]:
        sx, sy, ex, ey = p["x"], p["y"] - h, q["x"], q["y"] - h
        cx, cy = (sx + ex) / 2, min(sy, ey) - (40 + 0.28 * abs(ex - sx)) * lift
    else:
        up = q["line"] < p["line"]
        sx, sy = p["x"], p["y"] + (-h if up else h)
        ex, ey = q["x"], q["y"] + (h if up else -h)
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        dx, dy = ex - sx, ey - sy
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        side = 1 if (q["x"] < p["x"]) == up else -1
        cx, cy = mx + nx * L * 0.22 * side * lift, my + ny * L * 0.22 * side * lift
    return (sx, sy, cx, cy, ex, ey)

def d_of(a):
    sx, sy, cx, cy, ex, ey = a
    return f"M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"

def thread_style(w):
    return 2 + 26 * w, 0.22 + 0.78 * math.sqrt(w / 0.55)

def words_html(prefix, pos, fs, extra_cls=""):
    out = []
    for i, (wd, p) in enumerate(zip(WORDS, pos)):
        out.append(
            f'<div class="wslot {extra_cls}" style="left:{p["x"]}px;top:{p["y"]}px;font-size:{fs}px">'
            f'<span id="{prefix}-w{i}" class="w">{wd}</span></div>')
    return "\n    ".join(out)

def scene(cid, dur, css, body, js, extra_head=""):
    return f"""<template>
  <style>
    {FONT_FACES}
    #root {{ position: absolute; inset: 0; overflow: hidden; background: #0b0c0e; font-family: 'InterV', Inter, sans-serif; color: {INK}; }}
    .wslot {{ position: absolute; transform: translate(-50%, -50%); white-space: nowrap; font-weight: 700; letter-spacing: -0.01em; line-height: 1; }}
    .w {{ display: inline-block; }}
    .mono {{ font-family: 'MonoV', 'JetBrains Mono', monospace; }}
    .credit {{ position: absolute; left: 62px; top: 1312px; font-size: 22px; font-weight: 400; color: rgba(244,241,234,0.8); background: rgba(8,9,11,0.6); padding: 4px 10px; border-radius: 4px; }}
    .plate {{ position: absolute; left: 0; top: 0; }}
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

def rel(sid, k):
    """Time of word k (0-based) of scene sid, relative to its scene start."""
    ws = [w for w in T["words"] if w["scene"] == sid]
    return round(ws[k]["start"] - SC[sid]["start"], 2)

# --------------------------------------------------------------- photo framing
# Crosswalk photo 4445x2963. Hook/end framing: scale 0.75 -> 3334x2222, dog's head near x 700, y 900.
DOG = {"w": 3334, "h": 2222, "left": -1250, "top": -40}
HOOK_FS, HOOK_TOP, HOOK_LH = 80, 268, 128
HP = layout(HOOK_FS, HOOK_TOP, HOOK_LH)

# --------------------------------------------------------------- hook
def gen_hook():
    s = SC["hook"]; dur = s["length"]
    hook_words = [w for w in T["words"] if w["scene"] == "hook"][:11]
    t_it = rel("hook", 14); t_animal = rel("hook", 17); t_machine = rel("hook", 18)
    a = arc(HP[IT], HP[ANIMAL], HOOK_FS)
    boxes = []
    for i, p in enumerate(HP):
        bw, bh = p["w"] + 26, HOOK_FS * 1.18
        boxes.append(f'<div id="hook-box{i}" class="tok" style="left:{p["x"]-bw/2:.1f}px;top:{p["y"]-bh/2:.1f}px;width:{bw:.1f}px;height:{bh:.1f}px">'
                     f'<span class="mono tokn">{i+1}</span></div>')
    css = f"""
    #hook-cam {{ position: absolute; inset: 0; transform-origin: 700px 900px; }}
    #hook-photo {{ width: {DOG['w']}px; height: {DOG['h']}px; left: {DOG['left']}px; top: {DOG['top']}px; }}
    #hook-scrim {{ position: absolute; left: 0; top: 0; width: 1080px; height: 900px; background: linear-gradient(180deg, rgba(8,9,11,0.82) 0%, rgba(8,9,11,0.62) 60%, rgba(8,9,11,0) 100%); }}
    #hook-thread {{ position: absolute; inset: 0; overflow: visible; }}
    .tok {{ position: absolute; border: 2px solid rgba(244,241,234,0.55); border-radius: 4px; opacity: 0; }}
    .tokn {{ position: absolute; left: 0; top: -36px; font-size: 28px; color: rgba(244,241,234,0.7); }}
    #hook-dip {{ position: absolute; inset: 0; background: #000; opacity: 0; }}
    """
    body = f"""<div id="hook-cam">
      <img id="hook-photo" class="plate" src="assets/img/dog-crosswalk.jpg" alt="A stray dog lying on a zebra crossing" />
    </div>
    <div id="hook-scrim"></div>
    <svg id="hook-thread" width="1080" height="1920" viewBox="0 0 1080 1920" data-layout-ignore>
      <path id="hook-arc" d="{d_of(a)}" pathLength="1" fill="none" stroke="{AMBER}" stroke-width="7" stroke-linecap="butt" stroke-dasharray="1" stroke-dashoffset="1" />
    </svg>
    <div id="hook-words" data-layout-allow-overlap>
    {words_html("hook", HP, HOOK_FS)}
    </div>
    {''.join(boxes)}
    <div class="credit" data-layout-ignore>Photo: 玄史生, Keelung 2015 · CC0</div>
    <div id="hook-dip"></div>"""
    js = []
    js.append(f'tl.fromTo("#hook-cam", {{scale: 1}}, {{scale: 1.12, duration: D, ease: "power1.inOut"}}, 0);')
    for i, w in enumerate(hook_words):
        t0 = 0.12 if i == 0 else round(w["start"] - s["start"] - 0.04, 2)
        js.append(f'tl.fromTo("#hook-w{i}", {{opacity: 0.55}}, {{opacity: 1, duration: 0.14, ease: "power2.out"}}, {t0});')
    js.append(f'tl.to("#hook-w{IT}", {{color: "{AMBER}", duration: 0.25, ease: "power2.out"}}, {t_it});')
    js.append(f'tl.to("#hook-arc", {{attr: {{"stroke-dashoffset": 0}}, duration: 0.5, ease: "power3.out"}}, {t_animal - 0.15});')
    js.append(f'tl.to("#hook-w{ANIMAL}", {{color: "{AMBER}", duration: 0.25}}, {t_animal + 0.2});')
    # For a machine: words become numbered tokens, colours drop back to ink
    js.append(f'tl.to("#hook-arc", {{opacity: 0, duration: 0.3}}, {t_machine});')
    js.append(f'tl.to(["#hook-w{IT}", "#hook-w{ANIMAL}"], {{color: "{INK}", duration: 0.3}}, {t_machine});')
    js.append(f'tl.fromTo(".tok", {{opacity: 0, scale: 1.12}}, {{opacity: 1, scale: 1, duration: 0.35, ease: "expo.out", stagger: 0.05}}, {t_machine + 0.1});')
    js.append('tl.to("#hook-dip", {opacity: 0.4, duration: 0.1, ease: "none"}, D - 0.1);')
    return scene("hook", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- james
def gen_james():
    s = SC["james"]; dur = s["length"]
    t_q = rel("james", 7); t_attn_end = rel("james", 11); t_nobody = rel("james", 14)
    css = """
    #james-cam { position: absolute; inset: 0; transform-origin: 540px 470px; }
    #james-photo { width: 1560px; height: 2080px; left: -250px; top: -190px; }
    #james-quote { position: absolute; left: 90px; width: 900px; top: 960px; font-size: 62px; font-weight: 700; line-height: 1.14; letter-spacing: -0.015em; }
    #james-src { position: absolute; left: 82px; top: 1124px; font-size: 28px; color: rgba(244,241,234,0.85); background: rgba(8,9,11,0.6); padding: 2px 10px; border-radius: 4px; }
    #james-wrap { position: absolute; inset: 0; }
    """
    qwords = "“Everyone knows what attention is.”".split(" ")
    q = " ".join(f'<span id="james-q{i}" class="w">{w}</span>' for i, w in enumerate(qwords))
    body = f"""<div id="james-wrap">
    <div id="james-cam">
      <img id="james-photo" class="plate" src="assets/img/william-james.jpg" alt="William James, 1903" />
    </div>
    <div id="james-quote">{q}</div>
    <div id="james-src" class="mono">William James · The Principles of Psychology · 1890</div>
    <div class="credit" data-layout-ignore>Photo: Notman Studios, 1903 · Public domain</div>
    </div>"""
    js = ['tl.fromTo("#james-cam", {scale: 1.0}, {scale: 1.16, duration: D, ease: "power1.inOut"}, 0);']
    ts = [rel("james", k) for k in range(7, 12)]
    for i, t0 in enumerate(ts):
        js.append(f'tl.fromTo("#james-q{i}", {{opacity: 0, filter: "blur(6px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.14, ease: "power2.out"}}, {t0 - 0.05:.2f});')
    js.append(f'tl.to("#james-q3", {{color: "{AMBER}", duration: 0.25}}, {ts[3]:.2f});')
    js.append(f'tl.fromTo("#james-src", {{opacity: 0}}, {{opacity: 1, duration: 0.4, ease: "power2.out"}}, {t_q:.2f});')
    js.append(f'tl.to(["#james-quote", "#james-src"], {{opacity: 0.32, duration: 0.5, ease: "power2.inOut"}}, {t_nobody:.2f});')
    js.append('tl.to("#james-wrap", {opacity: 0, filter: "blur(8px)", duration: 0.16, ease: "power3.in"}, D - 0.16);')
    return scene("james", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- paper
def gen_paper():
    s = SC["paper"]; dur = s["length"]
    K = 1080 / 2550  # page px -> layout px
    def P(x, y): return x * K, y * K
    # phrase "based solely on attention mechanisms" and title, in page px
    ph = (599, 1687, 1210, 1728); ti = (881, 416, 1666, 488)
    t_attn = rel("paper", 8); t_their = rel("paper", 12); t_title = rel("paper", 16)
    pg_top = 330
    def cam(px, py, sc, cx=540, cy=760):
        X, Y = P(px, py); Y += pg_top
        return {"x": round(cx - sc * X, 1), "y": round(cy - sc * Y, 1), "scale": sc}
    c0 = {"x": 0, "y": 0, "scale": 1}
    c1 = cam((ph[0] + ph[2]) / 2, (ph[1] + ph[3]) / 2, 2.7)
    c2 = cam((ti[0] + ti[2]) / 2, (ti[1] + ti[3]) / 2, 2.35, cy=700)
    hx, hy = P(ph[0] - 8, ph[1] - 4); hw, hh = (ph[2] - ph[0] + 16) * K, (ph[3] - ph[1] + 8) * K
    tx, ty = P(ti[0], ti[3] + 10); tw = (ti[2] - ti[0]) * K
    css = f"""
    #paper-wrap {{ position: absolute; inset: 0; background: #ffffff; }}
    #paper-cam {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 0 0; }}
    #paper-page {{ position: absolute; left: 0; top: {pg_top}px; width: 1080px; height: {round(3300*K)}px; box-shadow: 0 30px 80px rgba(0,0,0,0.55); }}
    #paper-hl {{ position: absolute; left: {hx:.1f}px; top: {hy + pg_top:.1f}px; width: {hw:.1f}px; height: {hh:.1f}px; background: {AMBER}; mix-blend-mode: multiply; transform-origin: 0 50%; }}
    #paper-ul {{ position: absolute; left: {tx:.1f}px; top: {ty + pg_top:.1f}px; width: {tw:.1f}px; height: 4px; background: {AMBER}; transform-origin: 0 50%; }}
    #paper-flood {{ position: absolute; inset: 0; background: #0b0c0e; opacity: 0; }}
    """
    body = f"""<div id="paper-wrap">
    <div id="paper-cam">
      <img id="paper-page" src="assets/img/paper-p1.png" alt="First page of Attention Is All You Need, arXiv 1706.03762v1" />
      <div id="paper-hl"></div>
      <div id="paper-ul"></div>
    </div>
    <div class="credit" data-layout-ignore>Vaswani et al., Google · arXiv:1706.03762 · June 2017</div>
    <div id="paper-flood"></div>
    </div>"""
    js = [
        'tl.fromTo("#paper-wrap", {opacity: 0, filter: "blur(8px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.16, ease: "power2.out"}, 0);',
        f'tl.fromTo("#paper-cam", {json.dumps(c0)}, {{...{json.dumps(c1)}, duration: 2.6, ease: "power2.inOut"}}, 0.3);',
        f'tl.fromTo("#paper-hl", {{scaleX: 0, opacity: 0.55}}, {{scaleX: 1, opacity: 0.55, duration: 0.6, ease: "power3.out"}}, {t_attn - 0.1:.2f});',
        f'tl.to("#paper-cam", {{...{json.dumps(c2)}, duration: 1.8, ease: "power2.inOut"}}, {t_their - 0.2:.2f});',
        f'tl.fromTo("#paper-ul", {{scaleX: 0}}, {{scaleX: 1, duration: 0.55, ease: "power3.out"}}, {t_title - 0.05:.2f});',
        # zoom through the title into the stage
        f'tl.to("#paper-cam", {{...{json.dumps(cam((ti[0]+ti[2])/2, (ti[1]+ti[3])/2, 9, cy=700))}, duration: 0.55, ease: "power3.in"}}, D - 0.55);',
        'tl.to("#paper-flood", {opacity: 1, duration: 0.3, ease: "power2.in"}, D - 0.3);',
    ]
    return scene("paper", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- stage (match + weights + twist)
ST_FS, ST_TOP, ST_LH = 88, 560, 150
SP = layout(ST_FS, ST_TOP, ST_LH)
STAGE_BG = """<div id="{p}-bgwrap" class="bgwrap" data-layout-ignore><img id="{p}-bg" class="plate" data-layout-ignore src="assets/img/dog-crosswalk.jpg" alt="" style="width:5100px;height:3400px;left:-3950px;top:-700px" /></div>"""
STAGE_BG_CSS = ".bgwrap { position: absolute; inset: 0; opacity: 0.30; }"

def gen_stage():
    m, wt, tw = SC["match"], SC["weights"], SC["twist"]
    start = m["start"]; dur = round(m["length"] + wt["length"] + tw["length"], 2)
    o_w = round(wt["start"] - start, 2); o_t = round(tw["start"] - start, 2)
    R = lambda sid, k, off: round(rel(sid, k) + off, 2)
    t_it = R("match", 6, 0); t_query = R("match", 10, 0); t_every = R("match", 11, 0); t_label = R("match", 16, 0)
    t_better = R("match", 17, 0); t_thread = R("match", 23, 0)
    t_scores = R("weights", 1, o_w); t_100 = R("weights", 8, o_w); t_so = R("weights", 9, o_w); t_animal = R("weights", 16, o_w)
    t_one = R("twist", 2, o_t); t_wide = R("twist", 4, o_t); t_threads = R("twist", 7, o_t); t_street = R("twist", 11, o_t)
    t_same = R("twist", 12, o_t); t_newm = R("twist", 14, o_t)

    others = [i for i in range(len(WORDS)) if i != IT]
    paths, pct, keys = [], [], []
    for i in others:
        a = arc(SP[IT], SP[i], ST_FS)
        sw, op = thread_style(W_TIRED[i])
        paths.append(f'<path id="stage-t{i}" d="{d_of(a)}" pathLength="1" fill="none" stroke="{AMBER}" stroke-width="{sw:.1f}" stroke-opacity="{op:.2f}" stroke-linecap="butt" stroke-dasharray="1" stroke-dashoffset="1" />')
    for i, p in enumerate(SP):
        big = i in (ANIMAL, STREET)
        pct.append(f'<div class="pslot" style="left:{p["x"]}px;top:{p["y"] - ST_FS*0.5 - 30:.0f}px"><span id="stage-p{i}" class="mono pct{" big" if big else ""}">{round(W_TIRED[i]*100)}%</span></div>')
        if i != IT:
            keys.append(f'<div id="stage-k{i}" class="key" style="left:{p["x"] - 18:.1f}px;top:{p["y"] + ST_FS*0.42 + 8:.0f}px"></div>')
    itp = SP[IT]; an = SP[ANIMAL]; tir = SP[TIRED]
    # dot path (animal -> it): reuse animal arc reversed in JS
    a_an = arc(SP[IT], SP[ANIMAL], ST_FS)
    # bar
    BX, BY, BW = 90, 330, 900
    css = f"""
    {STAGE_BG_CSS}
    #stage-svg {{ position: absolute; inset: 0; overflow: visible; }}
    .pslot {{ position: absolute; transform: translate(-50%, -50%); white-space: nowrap; }}
    .pct {{ display: inline-block; font-size: 28px; color: rgba(244,241,234,0.6); }}
    .pct.big {{ font-size: 34px; }}
    .key {{ position: absolute; width: 36px; height: 4px; background: rgba(244,241,234,0.75); }}
    .lbl {{ position: absolute; font-size: 28px; white-space: nowrap; }}
    #stage-qlbl {{ left: {itp["x"] - 60:.0f}px; top: {itp["y"] + 58:.0f}px; color: {AMBER}; }}
    #stage-klbl {{ left: {an["x"] - 30:.0f}px; top: {an["y"] + 64:.0f}px; color: rgba(244,241,234,0.75); }}
    #stage-vlbl {{ left: {an["x"] + 40:.0f}px; top: {an["y"] + 150:.0f}px; color: {AMBER}; }}
    #stage-eq {{ left: {itp["x"] - 74:.0f}px; top: {itp["y"] + 58:.0f}px; color: {AMBER}; }}
    #stage-bar {{ position: absolute; left: {BX}px; top: {BY}px; width: {BW}px; height: 22px; }}
    .seg {{ position: absolute; top: 0; height: 22px; transform-origin: 0 50%; border-right: 3px solid #0b0c0e; }}
    .seg {{ left: 0; width: {BW}px; }}
    #stage-seg-a {{ background: {AMBER}; }}
    #stage-seg-s {{ background: rgba(244,241,234,0.72); }}
    #stage-seg-r {{ background: rgba(244,241,234,0.22); }}
    .blbl {{ position: absolute; top: 38px; font-size: 28px; white-space: nowrap; color: rgba(244,241,234,0.75); }}
    #stage-bl-a {{ left: 0; color: {AMBER}; }}
    #stage-bl-s {{ left: 0; top: -46px; }}
    #stage-bl-r {{ right: 0; text-align: right; }}
    #stage-btitle {{ position: absolute; left: 0; top: -100px; font-size: 28px; color: rgba(244,241,234,0.6); white-space: nowrap; }}
    #stage-roll {{ position: absolute; left: {tir["x"]:.1f}px; top: {tir["y"]:.0f}px; transform: translate(-50%, -50%); height: {ST_FS*1.15:.0f}px; overflow: hidden; font-size: {ST_FS}px; font-weight: 700; letter-spacing: -0.01em; }}
    #stage-rollin {{ display: flex; flex-direction: column; align-items: center; }}
    #stage-rollin span {{ display: block; height: {ST_FS*1.15:.0f}px; line-height: {ST_FS*1.15:.0f}px; }}
    #stage-tbox {{ position: absolute; left: {tir["x"] - tir["w"]/2 - 16:.0f}px; top: {tir["y"] - ST_FS*0.62:.0f}px; width: {tir["w"] + 32:.0f}px; height: {ST_FS*1.24:.0f}px; border: 3px solid rgba(244,241,234,0.85); border-radius: 6px; }}
    #stage-qlbl, #stage-klbl, #stage-vlbl, #stage-eq, #stage-r1, #stage-r2, #stage-tbox, .key, .pct, #stage-bar {{ opacity: 0; }}
    .reading {{ position: absolute; left: 0; width: 1080px; text-align: center; font-size: 32px; color: rgba(244,241,234,0.8); }}
    #stage-r1 {{ top: 1090px; }} #stage-r2 {{ top: 1140px; }}
    .hl {{ color: {AMBER}; }}
    """
    words = words_html("stage", SP, ST_FS).replace(f'<span id="stage-w{TIRED}" class="w">tired.</span>', f'<span id="stage-w{TIRED}" class="w" style="visibility:hidden">tired.</span>')
    body = f"""{STAGE_BG.format(p="stage")}
    <div id="stage-bar" data-layout-allow-overlap>
      <div id="stage-btitle" class="mono">what “it” pays attention to</div>
      <div id="stage-seg-a" class="seg"></div><div id="stage-seg-s" class="seg"></div><div id="stage-seg-r" class="seg"></div>
      <div id="stage-bl-a" class="blbl mono">animal <span id="stage-na">55</span>%</div>
      <div id="stage-bl-s" class="blbl mono">street <span id="stage-ns">15</span>%</div>
      <div id="stage-bl-r" class="blbl mono">rest <span id="stage-nr">30</span>% · = 100%</div>
    </div>
    <svg id="stage-svg" width="1080" height="1920" viewBox="0 0 1080 1920" data-layout-ignore>
      {"".join(paths)}
      <circle id="stage-dot" cx="{a_an[4]:.1f}" cy="{a_an[5]:.1f}" r="11" fill="{AMBER}" opacity="0" />
    </svg>
    <div id="stage-words" data-layout-allow-overlap>
    {words}
    </div>
    <div id="stage-roll" data-layout-allow-overflow><div id="stage-rollin"><span>tired.</span><span>wide.</span></div></div>
    <div id="stage-tbox"></div>
    <div id="stage-pcts" data-layout-allow-overlap>{"".join(pct)}</div>
    {"".join(keys)}
    <div id="stage-qlbl" class="lbl mono">↑ query</div>
    <div id="stage-klbl" class="lbl mono">↑ key</div>
    <div id="stage-vlbl" class="lbl mono">value</div>
    <div id="stage-eq" class="lbl mono">≈ animal</div>
    <div id="stage-r1" class="reading mono">too tired → “it” = the <span class="hl">animal</span></div>
    <div id="stage-r2" class="reading mono">too wide → “it” = the <span class="hl">street</span></div>"""

    js = []
    js.append('const AMBER = "%s", INK = "%s";' % (AMBER, INK))
    js.append(f'const W_T = {json.dumps(W_TIRED)}, W_W = {json.dumps(W_WIDE)};')
    js.append('const sw = w => 2 + 26 * w, so = w => 0.22 + 0.78 * Math.sqrt(w / 0.55);')
    # hidden-at-start states
    js.append('tl.fromTo("#stage-bgwrap", {scale: 1.08}, {scale: 1.0, duration: D, ease: "none"}, 0);')
    # entrance from the zoom-through: words sharpen in, staggered
    js.append('tl.fromTo("#stage-words .w, #stage-rollin", {opacity: 0, filter: "blur(10px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "expo.out", stagger: 0.04}, 0.05);')
    js.append('tl.set("#stage-words .w", {opacity: 0.38}, 1.2);')
    js.append(f'tl.to("#stage-words .w", {{opacity: 1, duration: 0.3}}, 1.2);')
    # it = query
    js.append(f'tl.to("#stage-w{IT}", {{color: AMBER, duration: 0.25}}, {t_it:.2f});')
    js.append(f'tl.fromTo("#stage-qlbl", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.45, ease: "expo.out"}}, {t_query:.2f});')
    # keys
    others_sel = json.dumps([f"#stage-k{i}" for i in others])
    js.append(f'tl.fromTo({others_sel}, {{opacity: 0, scaleX: 0}}, {{opacity: 1, scaleX: 1, duration: 0.35, ease: "expo.out", stagger: 0.07}}, {t_every:.2f});')
    js.append(f'tl.fromTo("#stage-klbl", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {t_label - 0.2:.2f});')
    # threads draw in order of weight
    order = sorted(others, key=lambda i: -W_TIRED[i])
    for n, i in enumerate(order):
        js.append(f'tl.to("#stage-t{i}", {{attr: {{"stroke-dashoffset": 0}}, duration: 0.5, ease: "power3.out"}}, {t_better + n * 0.12:.2f});')
    js.append(f'tl.to(["#stage-qlbl", "#stage-klbl"], {{opacity: 0, duration: 0.25}}, {t_thread:.2f});')
    js.append(f'tl.to(".key", {{opacity: 0, duration: 0.3}}, {t_thread:.2f});')
    js.append(f'tl.to("#stage-w{ANIMAL}", {{color: AMBER, duration: 0.3}}, {t_thread:.2f});')
    # weights: percentages + bar
    js.append(f'tl.fromTo(".pct", {{opacity: 0, y: 8}}, {{opacity: 1, y: 0, duration: 0.4, ease: "expo.out", stagger: 0.05}}, {t_scores:.2f});')
    js.append(f'tl.to("#stage-p{ANIMAL}", {{color: AMBER, duration: 0.2}}, {t_scores + 0.4:.2f});')
    js.append(f'tl.to("#stage-bar", {{opacity: 1, duration: 0.2}}, {t_100 - 0.9:.2f});')
    js.append(f'tl.set("#stage-bl-s", {{x: {BW*0.55:.0f}}}, 0);')
    js.append(f'tl.fromTo("#stage-seg-a", {{x: 0, scaleX: 0}}, {{x: 0, scaleX: 0.55, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.9:.2f});')
    js.append(f'tl.fromTo("#stage-seg-s", {{x: {BW*0.55:.0f}, scaleX: 0}}, {{x: {BW*0.55:.0f}, scaleX: 0.15, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.72:.2f});')
    js.append(f'tl.fromTo("#stage-seg-r", {{x: {BW*0.70:.0f}, scaleX: 0}}, {{x: {BW*0.70:.0f}, scaleX: 0.30, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.54:.2f});')
    js.append(f'tl.fromTo(".blbl, #stage-btitle", {{opacity: 0}}, {{opacity: 1, duration: 0.3, stagger: 0.1}}, {t_100 - 0.5:.2f});')
    # value: dot travels animal -> it along the animal thread
    sx, sy, cx, cy, ex, ey = a_an
    js.append(f'const qb = (t, a, b, c) => (1-t)*(1-t)*a + 2*(1-t)*t*b + t*t*c;')
    js.append(f'const dot = {{t: 0}};')
    js.append(f'tl.set("#stage-dot", {{opacity: 1}}, {t_so:.2f});')
    js.append(f'tl.fromTo(dot, {{t: 0}}, {{t: 1, duration: 1.0, ease: "power2.inOut", onUpdate: () => {{ const u = 1 - dot.t; document.querySelector("#stage-dot").setAttribute("cx", qb(u, {sx:.1f}, {cx:.1f}, {ex:.1f})); document.querySelector("#stage-dot").setAttribute("cy", qb(u, {sy:.1f}, {cy:.1f}, {ey:.1f})); }}}}, {t_so:.2f});')
    js.append(f'tl.fromTo("#stage-vlbl", {{opacity: 0}}, {{opacity: 1, duration: 0.3}}, {t_so + 0.1:.2f});')
    js.append(f'tl.to("#stage-dot", {{opacity: 0, duration: 0.15}}, {t_so + 1.0:.2f});')
    js.append(f'tl.fromTo("#stage-eq", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.45, ease: "expo.out"}}, {t_animal:.2f});')
    js.append(f'tl.to("#stage-vlbl", {{opacity: 0, duration: 0.25}}, {t_animal + 0.6:.2f});')
    # twist: box tired, roll to wide
    js.append(f'tl.to("#stage-eq", {{opacity: 0, duration: 0.25}}, {t_one - 0.3:.2f});')
    js.append(f'tl.fromTo("#stage-tbox", {{opacity: 0, scale: 1.15}}, {{opacity: 1, scale: 1, duration: 0.4, ease: "expo.out"}}, {t_one:.2f});')
    js.append(f'tl.fromTo("#stage-rollin", {{y: 0}}, {{y: -{ST_FS*1.15:.0f}, duration: 0.45, ease: "back.out(1.4)"}}, {t_wide - 0.05:.2f});')
    js.append(f'tl.to("#stage-tbox", {{opacity: 0, duration: 0.3}}, {t_threads - 0.2:.2f});')
    # threads swing
    for i in others:
        js.append(f'tl.to("#stage-t{i}", {{attr: {{"stroke-width": sw(W_W[{i}]), "stroke-opacity": so(W_W[{i}])}}, duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-w{ANIMAL}", {{color: INK, duration: 0.6}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-w{STREET}", {{color: AMBER, duration: 0.6}}, {t_threads + 0.4:.2f});')
    js.append(f'tl.to("#stage-p{ANIMAL}", {{color: "rgba(244,241,234,0.6)", duration: 0.4}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-p{STREET}", {{color: AMBER, duration: 0.4}}, {t_threads + 0.4:.2f});')
    # percentages count
    js.append('const pc = {u: 0};')
    js.append(f'tl.fromTo(pc, {{u: 0}}, {{u: 1, duration: 1.1, ease: "power2.inOut", onUpdate: () => {{ for (let i = 0; i < W_T.length; i++) {{ const v = W_T[i] + (W_W[i] - W_T[i]) * pc.u; const el = document.querySelector("#stage-p" + i); if (el) el.textContent = Math.round(v * 100) + "%"; }} document.querySelector("#stage-na").textContent = Math.round(55 + (14 - 55) * pc.u); document.querySelector("#stage-ns").textContent = Math.round(15 + (52 - 15) * pc.u); document.querySelector("#stage-nr").textContent = Math.round(30 + (34 - 30) * pc.u); }}}}, {t_threads:.2f});')
    # bar re-split: animal 14, street 52, rest 34
    js.append(f'tl.to("#stage-seg-a", {{scaleX: 0.14, backgroundColor: "rgba(244,241,234,0.72)", duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-seg-s", {{x: {BW*0.14:.0f}, scaleX: 0.52, backgroundColor: AMBER, duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-seg-r", {{x: {BW*0.66:.0f}, scaleX: 0.34, duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-bl-s", {{x: {BW*0.14:.0f}, color: AMBER, duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});')
    js.append(f'tl.to("#stage-bl-a", {{color: "rgba(244,241,234,0.75)", duration: 0.6}}, {t_threads:.2f});')
    # readings
    js.append(f'tl.fromTo("#stage-r1", {{opacity: 0}}, {{opacity: 1, duration: 0.35, ease: "power2.out"}}, {t_same:.2f});')
    js.append(f'tl.fromTo("#stage-r2", {{opacity: 0}}, {{opacity: 1, duration: 0.35, ease: "power2.out"}}, {t_newm:.2f});')
    return scene("stage", dur, css, body, "\n    ".join(js)), dur

# --------------------------------------------------------------- scale
def gen_scale():
    s = SC["scale"]; dur = s["length"]
    t_every = rel("scale", 1); t_once = rel("scale", 11); t_thousand = rel("scale", 13); t_million = rel("scale", 17)
    t_layer = rel("scale", 19)
    WP = [dict(p) for p in SP]
    words = words_html("scale", WP, ST_FS).replace(">tired.<", ">wide.<")
    pairs = [(i, j) for i in range(len(WORDS)) for j in range(i + 1, len(WORDS))]
    mesh = []
    for n, (i, j) in enumerate(pairs):
        a = arc(WP[i], WP[j], ST_FS, lift=0.8)
        mesh.append(f'<path class="mesh" d="{d_of(a)}" pathLength="1" fill="none" stroke="{AMBER}" stroke-width="2.5" stroke-opacity="0.45" stroke-dasharray="1" stroke-dashoffset="1" />')
    # it's own (wide) threads stay strong
    MX, MY, MS = 170, 470, 700
    css = f"""
    {STAGE_BG_CSS}
    #scale-sent {{ position: absolute; inset: 0; transform-origin: {MX}px {MY}px; }}
    #scale-svg {{ position: absolute; inset: 0; overflow: visible; }}
    #scale-mats {{ position: absolute; inset: 0; }}
    .mat {{ position: absolute; left: {MX}px; top: {MY}px; width: {MS}px; height: {MS}px; border: 2px solid rgba(244,241,234,0.5); background: #0d0e10; }}
    .mat canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    #scale-axis-x {{ position: absolute; left: {MX}px; top: {MY - 46}px; font-size: 28px; color: rgba(244,241,234,0.7); }}
    #scale-axis-y {{ position: absolute; left: {MX - 46}px; top: {MY + MS}px; font-size: 28px; color: rgba(244,241,234,0.7); transform: rotate(-90deg); transform-origin: 0 0; white-space: nowrap; }}
    .mat, #scale-axis-x, #scale-axis-y, #scale-count, #scale-layers {{ opacity: 0; }}
    #scale-count {{ position: absolute; left: 0; width: 1080px; top: 214px; text-align: center; font-size: 34px; color: rgba(244,241,234,0.8); }}
    #scale-num {{ color: {AMBER}; font-size: 52px; }}
    #scale-layers {{ position: absolute; left: 0; width: 1080px; top: 300px; text-align: center; font-size: 30px; color: rgba(244,241,234,0.75); }}
    """
    mats = "".join(f'<div id="scale-m{k}" class="mat"><canvas id="scale-c{k}" width="700" height="700"></canvas></div>' for k in range(4, -1, -1))
    body = f"""{STAGE_BG.format(p="scale")}
    <div id="scale-mats">{mats}</div>
    <div id="scale-sent">
      <svg id="scale-svg" width="1080" height="1920" viewBox="0 0 1080 1920" data-layout-ignore>{"".join(mesh)}</svg>
      <div id="scale-words" data-layout-allow-overlap data-layout-ignore>{words}</div>
    </div>
    <div id="scale-axis-x" class="mono">1,000 words →</div>
    <div id="scale-axis-y" class="mono">1,000 words →</div>
    <div id="scale-count" class="mono">= <span id="scale-num">0</span> comparisons</div>
    <div id="scale-layers" class="mono">… and again in every layer</div>"""
    js = []
    # draw matrices (static, seeded)
    js.append("""
    function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
    for (let k = 0; k < 5; k++) {
      const c = document.querySelector("#scale-c" + k); const g = c.getContext("2d"); const r = rng(1234 + k * 77);
      const N = 50, cs = 700 / N;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        let v = Math.pow(r(), 6) * 0.9; if (x === y) v = 0.35 + r() * 0.3; if (Math.abs(x - y) === 1) v += 0.15;
        g.fillStyle = "rgba(242,165,65," + Math.min(1, v).toFixed(3) + ")"; g.fillRect(x * cs + 0.5, y * cs + 0.5, cs - 1, cs - 1);
      }
    }""")
    js.append('tl.set("#scale-w7", {color: "%s"}, 0); tl.set("#scale-w5", {color: "%s"}, 0);' % (AMBER, AMBER))
    js.append(f'tl.to(".mesh", {{attr: {{"stroke-dashoffset": 0}}, duration: 0.5, ease: "power3.out", stagger: {round((t_once - t_every) / len(pairs), 3)}}}, {t_every:.2f});')
    # pull back: sentence shrinks into the top-left corner of the matrix
    js.append(f'tl.to("#scale-sent", {{scale: 0.07, x: 0, y: 0, duration: 1.2, ease: "power3.inOut"}}, {t_thousand - 0.3:.2f});')
    js.append(f'tl.to("#scale-sent", {{opacity: 0, duration: 0.4}}, {t_thousand + 0.7:.2f});')
    js.append(f'tl.fromTo("#scale-m0", {{opacity: 0, clipPath: "inset(0% 100% 100% 0%)"}}, {{opacity: 1, clipPath: "inset(0% 0% 0% 0%)", duration: 1.0, ease: "power2.inOut"}}, {t_thousand + 0.2:.2f});')
    js.append(f'tl.fromTo(["#scale-axis-x", "#scale-axis-y"], {{opacity: 0}}, {{opacity: 1, duration: 0.4}}, {t_thousand + 0.5:.2f});')
    js.append(f'tl.to("#scale-count", {{opacity: 1, duration: 0.3}}, {t_million - 0.35:.2f});')
    js.append('const ct = {v: 0};')
    js.append(f'tl.fromTo(ct, {{v: 0}}, {{v: 1000000, duration: 0.9, ease: "power2.out", onUpdate: () => {{ document.querySelector("#scale-num").textContent = Math.round(ct.v).toLocaleString("en-US"); }}}}, {t_million - 0.2:.2f});')
    for k in range(1, 5):
        js.append(f'tl.fromTo("#scale-m{k}", {{opacity: 0, x: 0, y: 0}}, {{opacity: {1 - k*0.18:.2f}, x: {k*24}, y: {-k*20}, duration: 0.6, ease: "expo.out"}}, {t_layer - 0.1 + k*0.12:.2f});')
    js.append(f'tl.to("#scale-layers", {{opacity: 1, duration: 0.35}}, {t_layer + 0.2:.2f});')
    js.append(f'tl.to(["#scale-axis-x", "#scale-axis-y"], {{opacity: 0, duration: 0.25}}, {t_layer:.2f});')
    js.append('tl.to("#scale-mats, #scale-axis-x, #scale-axis-y, #scale-count, #scale-layers", {opacity: 0, filter: "blur(8px)", duration: 0.18, ease: "power3.in"}, D - 0.18);')
    return scene("scale", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- end
def gen_end():
    s = SC["end"]; dur = s["length"]
    t_every = rel("end", 2); t_are = rel("end", 8)
    pairs = [(i, j) for i in range(len(WORDS)) for j in range(i + 1, len(WORDS))]
    mesh = "".join(f'<path class="emesh" d="{d_of(arc(HP[i], HP[j], HOOK_FS, lift=0.8))}" pathLength="1" fill="none" stroke="{AMBER}" stroke-width="2" stroke-opacity="0.35" stroke-dasharray="1" stroke-dashoffset="1" />' for i, j in pairs)
    a = arc(HP[IT], HP[ANIMAL], HOOK_FS)
    itp = HP[IT]
    css = f"""
    #end-iris {{ position: absolute; inset: 0; }}
    #end-cam {{ position: absolute; inset: 0; transform-origin: 700px 900px; }}
    #end-photo {{ width: {DOG['w']}px; height: {DOG['h']}px; left: {DOG['left']}px; top: {DOG['top']}px; }}
    #end-scrim {{ position: absolute; left: 0; top: 0; width: 1080px; height: 900px; background: linear-gradient(180deg, rgba(8,9,11,0.82) 0%, rgba(8,9,11,0.62) 60%, rgba(8,9,11,0) 100%); }}
    #end-svg {{ position: absolute; inset: 0; overflow: visible; }}
    """
    body = f"""<div id="end-iris">
    <div id="end-cam"><img id="end-photo" class="plate" src="assets/img/dog-crosswalk.jpg" alt="The dog on the crossing" /></div>
    <div id="end-scrim"></div>
    <svg id="end-svg" width="1080" height="1920" viewBox="0 0 1080 1920" data-layout-ignore>
      {mesh}
      <path id="end-arc" d="{d_of(a)}" pathLength="1" fill="none" stroke="{AMBER}" stroke-width="8" stroke-linecap="butt" stroke-dasharray="1" stroke-dashoffset="1" />
    </svg>
    <div id="end-words" data-layout-allow-overlap>{words_html("end", HP, HOOK_FS)}</div>
    </div>"""
    js = [
        f'tl.fromTo("#end-iris", {{clipPath: "circle(0px at {itp["x"]:.0f}px {itp["y"]:.0f}px)"}}, {{clipPath: "circle(2300px at {itp["x"]:.0f}px {itp["y"]:.0f}px)", duration: 0.7, ease: "power3.in"}}, 0);',
        'tl.fromTo("#end-cam", {scale: 1.12}, {scale: 1.0, duration: D, ease: "power1.out"}, 0);',
        f'tl.set("#end-w{IT}", {{color: "{AMBER}"}}, 0);',
        f'tl.to(".emesh", {{attr: {{"stroke-dashoffset": 0}}, duration: 0.45, ease: "power3.out", stagger: 0.035}}, {t_every:.2f});',
        f'tl.to(".emesh", {{attr: {{"stroke-opacity": 0.12}}, duration: 0.6}}, {t_are - 0.2:.2f});',
        f'tl.to("#end-arc", {{attr: {{"stroke-dashoffset": 0}}, duration: 0.6, ease: "power3.out"}}, {t_are:.2f});',
        f'tl.to("#end-w{ANIMAL}", {{color: "{AMBER}", duration: 0.3}}, {t_are + 0.4:.2f});',
    ]
    return scene("end", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- captions
FIX = {"is": "Is", "Need.": "Need."}
def gen_captions():
    total = T["total"]
    ws = [w for w in T["words"]]
    hook_start_skip = 11  # the hook sentence is printed on screen; no caption under it
    ws = ws[hook_start_skip:]
    # restore script wording for the paper title
    for k, w in enumerate(ws):
        if w["scene"] == "paper" and w["text"] == "is" and k + 1 < len(ws) and ws[k + 1]["text"] == "All":
            w["text"] = "Is"
        if w["text"] == "1890,": w["text"] = "1890,"
        if w["scene"] == "scale" and w["text"] == "and": w["text"] = "And"
    groups, cur = [], []
    for k, w in enumerate(ws):
        if cur:
            prev = cur[-1]
            brk = (prev["scene"] != w["scene"] or prev["text"][-1] in ".?!,:" and len(cur) >= 2
                   or w["start"] - prev["end"] >= 0.3 or len(cur) >= 4)
            if prev["text"][-1] in ".?!": brk = True
            if brk:
                groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    html, js = [], []
    for g_i, g in enumerate(groups):
        g0 = round(g[0]["start"] - 0.12, 2)
        nxt = groups[g_i + 1][0]["start"] - 0.12 if g_i + 1 < len(groups) else total
        same_scene_next = g_i + 1 < len(groups) and groups[g_i + 1][0]["scene"] == g[0]["scene"]
        g1 = round(min(nxt, g[-1]["end"] + (0.6 if same_scene_next else 0.35)), 2)
        if not same_scene_next:
            sc_end = SC[g[0]["scene"]]["start"] + SC[g[0]["scene"]]["length"]
            g1 = round(min(g1, sc_end - 0.05, nxt), 2)
        spans = " ".join(f'<span id="cap-{g_i}-{k}" class="cw">{w["text"]}</span>' for k, w in enumerate(g))
        html.append(f'<div id="cap-g{g_i}" class="clip capg{" onpage" if g[0]["scene"] == "paper" else ""}" data-start="{g0}" data-duration="{round(g1 - g0, 2)}" data-track-index="0"><div class="capin">{spans}</div></div>')
        for k, w in enumerate(g):
            js.append(f'tl.to("#cap-{g_i}-{k}", {{color: "rgba(244,241,234,1)", duration: 0.08, ease: "none"}}, {round(w["start"], 2)});')
    css = """
    .capg { position: absolute; left: 0; top: 1214px; width: 1080px; text-align: center; }
    .capin { display: inline-block; max-width: 900px; font-size: 44px; font-weight: 700; line-height: 1.25; letter-spacing: -0.005em; text-shadow: 0 2px 14px rgba(0,0,0,0.75), 0 0 2px rgba(0,0,0,0.6); }
    .cw { color: rgba(244,241,234,0.62); }
    .capg.onpage .capin { background: rgba(8,9,11,0.72); padding: 6px 18px; border-radius: 6px; text-shadow: none; }
    """
    out = f"""<template>
  <style>
    {FONT_FACES}
    #root {{ position: absolute; inset: 0; font-family: 'InterV', Inter, sans-serif; }}
    {css}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920" data-start="0" data-duration="{total}">
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

# --------------------------------------------------------------- write
open("compositions/hook.html", "w").write(gen_hook())
open("compositions/james.html", "w").write(gen_james())
open("compositions/paper.html", "w").write(gen_paper())
stage_html, stage_dur = gen_stage()
open("compositions/stage.html", "w").write(stage_html)
open("compositions/scale.html", "w").write(gen_scale())
open("compositions/end.html", "w").write(gen_end())
cap_html, ng = gen_captions()
open("compositions/captions.html", "w").write(cap_html)

hosts = [("hook", SC["hook"]["start"], SC["hook"]["length"]),
         ("james", SC["james"]["start"], SC["james"]["length"]),
         ("paper", SC["paper"]["start"], SC["paper"]["length"]),
         ("stage", SC["match"]["start"], stage_dur),
         ("scale", SC["scale"]["start"], SC["scale"]["length"]),
         ("end", SC["end"]["start"], SC["end"]["length"])]
host_html = "\n".join(
    f'      <div id="{h}" data-composition-id="{h}" data-composition-src="compositions/{h}.html" data-start="{s}" data-duration="{d}" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920" style="z-index:{2 + n}"></div>'
    for n, (h, s, d) in enumerate(hosts))
voice_html = "\n".join(
    f'      <audio id="vo-{s["id"]}" class="clip" src="assets/voice/{s["id"]}.wav" data-start="{round(s["start"] + s["voiceAt"], 2)}" data-duration="{s["voiceDur"]}" data-track-index="3" data-volume="1"></audio>'
    for s in T["scenes"])
sfx = json.load(open("tmp/sfx_plan.json")) if os.path.exists("tmp/sfx_plan.json") else []
sfx_html = "\n".join(
    f'      <audio id="sfx-{n}" class="clip" src="{c["src"]}" data-start="{c["t"]}" data-duration="{c["dur"]}"{(' data-media-start="' + str(c["ms"]) + '"') if c.get("ms") else ""} data-track-index="4" data-volume="{c["vol"]}"></audio>'
    for n, c in enumerate(sfx))
music = json.load(open("tmp/music_plan.json")) if os.path.exists("tmp/music_plan.json") else None
music_html = (f'      <audio id="music-bed" class="clip" src="{music["src"]}" data-start="0" data-duration="{T["total"]}" data-media-start="{music.get("mediaStart", 0)}" data-track-index="5" data-volume="{music["vol"]}" data-fade-in="1.5" data-fade-out="3"></audio>' if music else "")

index = f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0b0c0e; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{T['total']}" data-width="1080" data-height="1920">
{host_html}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{T['total']}" data-track-index="2" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index:20"></div>
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
print("ok; caption groups:", ng, "stage dur", stage_dur)
