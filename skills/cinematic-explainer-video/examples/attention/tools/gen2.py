# v2: one Three.js world under the whole film + HTML layers on top.
# Reuses the caption and paper builders from gen.py (loaded without running its writer).
import json, os, re

src = open("tools/gen.py").read().split("# --------------------------------------------------------------- write")[0]
src = src.replace("hook_start_skip = 11", "hook_start_skip = 0")
G = {}
exec(src, G)
T, SC, rel, scene, AMBER, INK = G["T"], G["SC"], G["rel"], G["scene"], G["AMBER"], G["INK"]
W_TIRED, W_WIDE, WORDS = G["W_TIRED"], G["W_WIDE"], G["WORDS"]
TOTAL = T["total"]

def g(sid, k):  # global time of word k in scene sid
    return round(SC[sid]["start"] + rel(sid, k), 3)

A = {
    "hookIt": g("hook", 14), "hookAnimal": g("hook", 17), "hookMachine": g("hook", 18),
    "hookEnd": SC["james"]["start"],
    "stageCut": round(SC["match"]["start"] - 0.45, 2),
    "mIt": g("match", 6), "mQuestion": g("match", 10), "mEvery": g("match", 11), "mLabel": g("match", 17),
    "mBetter": g("match", 18), "mThread": g("match", 25),
    "wScores": g("weights", 1), "w100": g("weights", 8), "wSo": g("weights", 9), "wAnimal": g("weights", 17),
    "twOne": g("twist", 2), "twWide": g("twist", 5), "twThreads": g("twist", 7), "twSame": g("twist", 12), "twNewm": g("twist", 14),
    "scStart": SC["scale"]["start"], "scEvery": g("scale", 1), "scOnce": g("scale", 11), "scThousand": g("scale", 13),
    "scMillion": g("scale", 17), "scLayer": g("scale", 20),
    "endStart": SC["end"]["start"], "eEvery": g("end", 2), "eAre": g("end", 8),
}
hook_ws = [w["start"] for w in T["words"] if w["scene"] == "hook"][:11]
cfg = {"total": TOTAL, "anchors": A, "words": WORDS, "wTired": W_TIRED, "wWide": W_WIDE, "hookWordStarts": hook_ws}
os.makedirs("compositions", exist_ok=True)
world = open("tools/world.template.html").read().replace("__CONFIG__", json.dumps(cfg)).replace("__DUR__", str(TOTAL))
open("compositions/world.html", "w").write(world)

FONT_FACES = G["FONT_FACES"]

# --------------------------------------------------------------- hook title (over the 3D hall)
def gen_hookui():
    dur = SC["hook"]["length"]
    css = """
    #hookui-title { position: absolute; left: 0; width: 1080px; top: 210px; text-align: center; font-size: 58px; font-weight: 700; letter-spacing: -0.015em; color: #F4F1EA; text-shadow: 0 2px 18px rgba(0,0,0,0.7); }
    #hookui-it { color: %s; }
    """ % AMBER
    body = '<div id="hookui-title">What does “<span id="hookui-it">it</span>” mean?</div>'
    js = f"""tl.fromTo("#hookui-title", {{opacity: 1}}, {{opacity: 0, filter: "blur(6px)", duration: 0.25, ease: "power3.in"}}, {rel('hook', 11) - 0.2:.2f});"""
    return scene("hookui", dur, css, body, js)

# --------------------------------------------------------------- james: parallax portrait over the hall
def gen_james2():
    s = SC["james"]; dur = s["length"]
    ts = [rel("james", k) for k in range(7, 12)]
    t_nobody = rel("james", 14)
    css = """
    #james-wrap { position: absolute; inset: 0; background: #0b0c0e; }
    #james-bgcam, #james-fgcam { position: absolute; inset: 0; transform-origin: 540px 520px; }
    .jplate { position: absolute; width: 1560px; height: 2080px; left: -250px; top: -190px; }
    #james-quote { position: absolute; left: 90px; width: 900px; top: 960px; font-size: 62px; font-weight: 700; line-height: 1.14; letter-spacing: -0.015em; text-shadow: 0 2px 18px rgba(0,0,0,0.6); }
    #james-src { position: absolute; left: 82px; top: 1124px; font-size: 28px; color: rgba(244,241,234,0.85); background: rgba(8,9,11,0.6); padding: 2px 10px; border-radius: 4px; }
    """
    qwords = "“Everyone knows what attention is.”".split(" ")
    q = " ".join(f'<span id="james-q{i}" class="w">{w}</span>' for i, w in enumerate(qwords))
    body = f"""<div id="james-wrap">
      <div id="james-bgcam"><img id="james-photo" class="jplate" src="assets/img/william-james.jpg" alt="William James, 1903" data-layout-ignore /></div>
      <div id="james-fgcam"><img id="james-cut" class="jplate" src="assets/img/william-james-cut.png" alt="" data-layout-ignore /></div>
      <div id="james-quote">{q}</div>
      <div id="james-src" class="mono">William James · The Principles of Psychology · 1890</div>
      <div class="credit" data-layout-ignore>Photo: Notman Studios, 1903 · Public domain</div>
    </div>"""
    js = [
        'tl.fromTo("#james-wrap", {opacity: 0}, {opacity: 1, duration: 0.55, ease: "power2.inOut"}, 0);',
        # parallax: the background drifts less than the man
        'tl.fromTo("#james-bgcam", {scale: 1.02, x: 0}, {scale: 1.07, x: 10, duration: D, ease: "power1.inOut"}, 0);',
        'tl.fromTo("#james-fgcam", {scale: 1.0, x: 0, y: 0}, {scale: 1.14, x: -26, y: -8, duration: D, ease: "power1.inOut"}, 0);',
    ]
    for i, t0 in enumerate(ts):
        js.append(f'tl.fromTo("#james-q{i}", {{opacity: 0, filter: "blur(6px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.14, ease: "power2.out"}}, {t0 - 0.05:.2f});')
    js.append(f'tl.to("#james-q3", {{color: "{AMBER}", duration: 0.25}}, {ts[3]:.2f});')
    js.append(f'tl.fromTo("#james-src", {{opacity: 0}}, {{opacity: 1, duration: 0.4, ease: "power2.out"}}, {ts[0]:.2f});')
    js.append(f'tl.to(["#james-quote", "#james-src"], {{opacity: 0.32, duration: 0.5, ease: "power2.inOut"}}, {t_nobody:.2f});')
    js.append('tl.to("#james-wrap", {opacity: 0, filter: "blur(8px)", duration: 0.16, ease: "power3.in"}, D - 0.16);')
    return scene("james", dur, css, body, "\n    ".join(js))

# --------------------------------------------------------------- paper: ends by dissolving into the world
def gen_paper2():
    html = G["gen_paper"]()
    html = html.replace("tl.to(\"#paper-flood\", {opacity: 1, duration: 0.3, ease: \"power2.in\"}, D - 0.3);",
                        "tl.to(\"#paper-wrap\", {opacity: 0, duration: 0.42, ease: \"power2.in\"}, D - 0.42);")
    html = html.replace('<div id="paper-flood"></div>', "")
    html = html.replace("#paper-wrap {{ position: absolute; inset: 0; }}", "")
    html = re.sub(r"#paper-wrap \{ position: absolute; inset: 0;[^}]*\}", "#paper-wrap { position: absolute; inset: 0; background: #ffffff; }", html)
    # extend the paper slot so its dissolve overlaps the world's stage reveal
    return html

# --------------------------------------------------------------- stage UI: the 100% bar + readings
def gen_stageui():
    m, wt, tw = SC["match"], SC["weights"], SC["twist"]
    start = m["start"]; dur = round(m["length"] + wt["length"] + tw["length"], 2)
    o_w = round(wt["start"] - start, 2); o_t = round(tw["start"] - start, 2)
    R = lambda sid, k, off: round(rel(sid, k) + off, 2)
    t_100 = R("weights", 8, o_w); t_animal = R("weights", 17, o_w)
    t_one = R("twist", 2, o_t); t_threads = R("twist", 7, o_t); t_same = R("twist", 12, o_t); t_newm = R("twist", 14, o_t)
    BX, BY, BW = 90, 300, 900
    css = f"""
    #stageui-bar {{ position: absolute; left: {BX}px; top: {BY}px; width: {BW}px; height: 22px; opacity: 0; }}
    .seg {{ position: absolute; top: 0; left: 0; width: {BW}px; height: 22px; transform-origin: 0 50%; border-right: 3px solid #06080b; }}
    #stageui-seg-a {{ background: {AMBER}; }}
    #stageui-seg-s {{ background: rgba(244,241,234,0.72); }}
    #stageui-seg-r {{ background: rgba(244,241,234,0.22); }}
    .blbl {{ position: absolute; top: 38px; font-size: 28px; white-space: nowrap; color: rgba(244,241,234,0.78); }}
    #stageui-bl-a {{ left: 0; color: {AMBER}; }}
    #stageui-bl-s {{ left: 0; top: -46px; }}
    #stageui-bl-r {{ right: 0; text-align: right; }}
    #stageui-btitle {{ position: absolute; left: 0; top: -100px; font-size: 28px; color: rgba(244,241,234,0.62); white-space: nowrap; }}
    .reading {{ position: absolute; left: 0; width: 1080px; text-align: center; font-size: 32px; color: rgba(244,241,234,0.85); opacity: 0; text-shadow: 0 2px 12px rgba(0,0,0,0.8); }}
    #stageui-r0 {{ top: 1134px; }} #stageui-r1 {{ top: 1110px; }} #stageui-r2 {{ top: 1156px; }}
    .hl {{ color: {AMBER}; }}
    """
    body = f"""<div id="stageui-bar" data-layout-allow-overlap>
      <div id="stageui-btitle" class="mono">what “it” pays attention to</div>
      <div id="stageui-seg-a" class="seg"></div><div id="stageui-seg-s" class="seg"></div><div id="stageui-seg-r" class="seg"></div>
      <div id="stageui-bl-a" class="blbl mono">animal <span id="stageui-na">55</span>%</div>
      <div id="stageui-bl-s" class="blbl mono">street <span id="stageui-ns">15</span>%</div>
      <div id="stageui-bl-r" class="blbl mono">rest <span id="stageui-nr">30</span>% · = 100%</div>
    </div>
    <div id="stageui-r0" class="reading mono">“it” ≈ the <span class="hl">animal</span></div>
    <div id="stageui-r1" class="reading mono">too tired → “it” = the <span class="hl">animal</span></div>
    <div id="stageui-r2" class="reading mono">too wide → “it” = the <span class="hl">street</span></div>"""
    js = [
        f'tl.set("#stageui-bl-s", {{x: {BW*0.55:.0f}}}, 0);',
        f'tl.to("#stageui-bar", {{opacity: 1, duration: 0.2}}, {t_100 - 0.9:.2f});',
        f'tl.fromTo("#stageui-seg-a", {{x: 0, scaleX: 0}}, {{x: 0, scaleX: 0.55, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.9:.2f});',
        f'tl.fromTo("#stageui-seg-s", {{x: {BW*0.55:.0f}, scaleX: 0}}, {{x: {BW*0.55:.0f}, scaleX: 0.15, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.72:.2f});',
        f'tl.fromTo("#stageui-seg-r", {{x: {BW*0.70:.0f}, scaleX: 0}}, {{x: {BW*0.70:.0f}, scaleX: 0.30, duration: 0.5, ease: "power3.out"}}, {t_100 - 0.54:.2f});',
        f'tl.fromTo(".blbl, #stageui-btitle", {{opacity: 0}}, {{opacity: 1, duration: 0.3, stagger: 0.1}}, {t_100 - 0.5:.2f});',
        f'tl.fromTo("#stageui-r0", {{opacity: 0}}, {{opacity: 1, duration: 0.35}}, {t_animal:.2f});',
        f'tl.to("#stageui-r0", {{opacity: 0, duration: 0.25}}, {t_one - 0.3:.2f});',
        'const pc = {u: 0};',
        f'tl.fromTo(pc, {{u: 0}}, {{u: 1, duration: 1.1, ease: "power2.inOut", onUpdate: () => {{ document.querySelector("#stageui-na").textContent = Math.round(55 + (14 - 55) * pc.u); document.querySelector("#stageui-ns").textContent = Math.round(15 + (52 - 15) * pc.u); document.querySelector("#stageui-nr").textContent = Math.round(30 + (34 - 30) * pc.u); }}}}, {t_threads:.2f});',
        f'tl.to("#stageui-seg-a", {{scaleX: 0.14, backgroundColor: "rgba(244,241,234,0.72)", duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});',
        f'tl.to("#stageui-seg-s", {{x: {BW*0.14:.0f}, scaleX: 0.52, backgroundColor: "{AMBER}", duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});',
        f'tl.to("#stageui-seg-r", {{x: {BW*0.66:.0f}, scaleX: 0.34, duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});',
        f'tl.to("#stageui-bl-s", {{x: {BW*0.14:.0f}, color: "{AMBER}", duration: 1.1, ease: "power2.inOut"}}, {t_threads:.2f});',
        f'tl.to("#stageui-bl-a", {{color: "rgba(244,241,234,0.78)", duration: 0.6}}, {t_threads:.2f});',
        f'tl.fromTo("#stageui-r1", {{opacity: 0}}, {{opacity: 1, duration: 0.35}}, {t_same:.2f});',
        f'tl.fromTo("#stageui-r2", {{opacity: 0}}, {{opacity: 1, duration: 0.35}}, {t_newm:.2f});',
        'tl.to(["#stageui-bar", "#stageui-r1", "#stageui-r2"], {opacity: 0, duration: 0.3}, D - 0.3);',
    ]
    return scene("stageui", dur, css, body, "\n    ".join(js)), start, dur

# --------------------------------------------------------------- scale UI: the counter
def gen_scaleui():
    s = SC["scale"]; dur = s["length"]
    t_million = rel("scale", 17); t_layer = rel("scale", 20)
    css = f"""
    #scaleui-count {{ position: absolute; left: 0; width: 1080px; top: 214px; text-align: center; font-size: 34px; color: rgba(244,241,234,0.85); opacity: 0; text-shadow: 0 2px 14px rgba(0,0,0,0.8); }}
    #scaleui-num {{ color: {AMBER}; font-size: 56px; }}
    #scaleui-layers {{ position: absolute; left: 0; width: 1080px; top: 300px; text-align: center; font-size: 30px; color: rgba(244,241,234,0.8); opacity: 0; text-shadow: 0 2px 14px rgba(0,0,0,0.8); }}
    """
    body = """<div id="scaleui-count" class="mono">1,000 words × 1,000 words = <span id="scaleui-num">0</span></div>
    <div id="scaleui-layers" class="mono">comparisons — again in every layer</div>"""
    js = [
        f'tl.to("#scaleui-count", {{opacity: 1, duration: 0.3}}, {t_million - 1.4:.2f});',
        'const ct = {v: 0};',
        f'tl.fromTo(ct, {{v: 0}}, {{v: 1000000, duration: 0.9, ease: "power2.out", onUpdate: () => {{ document.querySelector("#scaleui-num").textContent = Math.round(ct.v).toLocaleString("en-US"); }}}}, {t_million - 0.2:.2f});',
        f'tl.to("#scaleui-layers", {{opacity: 1, duration: 0.35}}, {t_layer - 0.1:.2f});',
        'tl.to(["#scaleui-count", "#scaleui-layers"], {opacity: 0, filter: "blur(6px)", duration: 0.25, ease: "power3.in"}, D - 0.25);',
    ]
    return scene("scaleui", dur, css, body, "\n    ".join(js))

def clear_bg(html):
    assert "background: #0b0c0e; font-family" in html
    return html.replace("background: #0b0c0e; font-family", "background: transparent; font-family", 1)
open("compositions/hookui.html", "w").write(clear_bg(gen_hookui()))
open("compositions/james.html", "w").write(gen_james2())
open("compositions/paper.html", "w").write(gen_paper2())
stageui, st_start, st_dur = gen_stageui()
open("compositions/stageui.html", "w").write(clear_bg(stageui))
open("compositions/scaleui.html", "w").write(clear_bg(gen_scaleui()))
cap_html, ng = G["gen_captions"]()
open("compositions/captions.html", "w").write(cap_html)
for old in ["hook", "stage", "scale", "end"]:
    p = f"compositions/{old}.html"
    if os.path.exists(p): os.remove(p)

hosts = [
    ("world", 0, TOTAL, 1, "graphics"),
    ("hookui", SC["hook"]["start"], SC["hook"]["length"], 3, "graphics"),
    ("james", SC["james"]["start"], SC["james"]["length"], 4, "graphics"),
    ("paper", SC["paper"]["start"], SC["paper"]["length"], 4, "graphics"),
    ("stageui", st_start, st_dur, 3, "graphics"),
    ("scaleui", SC["scale"]["start"], SC["scale"]["length"], 3, "graphics"),
]
host_html = "\n".join(
    f'      <div id="{h}" data-composition-id="{h}" data-composition-src="compositions/{h}.html" data-start="{s}" data-duration="{d}" data-track-index="{n}" data-track-kind="{k}" data-width="1080" data-height="1920" style="z-index:{z}"></div>'
    for n, (h, s, d, z, k) in enumerate(hosts))
voice_html = "\n".join(
    f'      <audio id="vo-{s["id"]}" class="clip" src="assets/voice/{s["id"]}.wav" data-start="{round(s["start"] + s["voiceAt"], 2)}" data-duration="{s["voiceDur"]}" data-track-index="7" data-volume="1"></audio>'
    for s in T["scenes"])
sfx = json.load(open("tmp/sfx_plan.json"))
sfx_html = "\n".join(
    f'      <audio id="sfx-{n}" class="clip" src="{c["src"]}" data-start="{c["t"]}" data-duration="{c["dur"]}"{(" data-media-start=" + chr(34) + str(c["ms"]) + chr(34)) if c.get("ms") else ""} data-track-index="8" data-volume="{c["vol"]}"></audio>'
    for n, c in enumerate(sfx))
music = json.load(open("tmp/music_plan.json"))
music_html = f'      <audio id="music-bed" class="clip" src="{music["src"]}" data-start="0" data-duration="{TOTAL}" data-track-index="9" data-volume="{music["vol"]}" data-fade-in="1.5" data-fade-out="3"></audio>'

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
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{TOTAL}" data-track-index="6" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index:20"></div>
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
print("ok; captions", ng, "anchors", json.dumps(A)[:300])
