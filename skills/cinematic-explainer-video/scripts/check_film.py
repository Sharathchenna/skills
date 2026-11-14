#!/usr/bin/env python3
"""Measured QA of the final MP4 (ffprobe/ffmpeg only; no Python packages needed).

  python3 -I tools/check_film.py renders/film.mp4 [--project DIR] [--profile tiktok|reels|both]
                                 [--sheet OUT.png] [--json [OUT.json]]
  python3 -I tools/check_film.py --self-test

Checks (thresholds.json keys in brackets; FAIL = hard, exit 1):
  container   1080x1920, 30/60 fps, h264, yuv420p, one AAC 48 kHz audio stream, audio covers video +-0.25 s,
              moov before mdat (faststart, warn)                                                   [film]
  duration    45-90 s warn outside; FAIL above the profile's hard max                              [duration]
  final hold  with DIR/timeline.json: last word ends >= 2 s before the end                         [finalHold]
  frame 0     mean luma (0-255 full range) > 12                                                    [frame0MinLuma]
  black       ffmpeg blackdetect: no black stretch mid-film (one ending at the very end only warns) [blackDetect]
  frozen      ffmpeg freezedetect: stretches > 1 s outside the final hold (warn)                   [freezeDetect]
  loudness    integrated -14 +-1.5 LUFS, true peak <= -1.0 dBTP, on the encoded file                [loudness]
  spread      P90 - P10 of 200 ms RMS windows >= 9 dB (voice stands out from the bed; warn)        [voiceBedSpread]
--sheet writes a contact sheet (a frame every ~3 s plus the last frame) with the platform safe zones drawn on
every frame: red bands where app UI covers the picture, a dashed 774 px centred box for text. Look at it.
What this cannot see: text size, overlap, contrast, caption timing (needs a DOM probe), and nobody listened.
"""
import argparse, array, json, math, os, re, struct, subprocess, sys, tempfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "thresholds.json")) as _fh:
    TH = json.load(_fh)
tv = lambda k: TH[k]["value"]


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


class Results:
    def __init__(self):
        self.items = []

    def add(self, name, status, value=None, threshold=None, detail=""):
        self.items.append({"check": name, "status": status, "value": value, "threshold": threshold, "detail": detail})

    def n(self, status):
        return sum(1 for i in self.items if i["status"] == status)

    def print(self):
        for i in self.items:
            v = "" if i["value"] is None else f"{i['value']}"
            t = "" if i["threshold"] is None else f"(want {i['threshold']})"
            print(f"{i['status'].upper():5s} {i['check']:22s} {v:>14s} {t:28s} {i['detail']}")

# ---------------------------------------------------------------- measurements

def probe(path):
    p = sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    if p.returncode:
        sys.exit(f"ffprobe failed: {p.stderr.decode()[:300]}")
    return json.loads(p.stdout)


def rate(s):
    try:
        a, b = s.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except (ValueError, AttributeError):
        return 0.0


def atom_order(path):
    """Top-level MP4 boxes in order (to see whether moov comes before mdat)."""
    out = []
    with open(path, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        pos = 0
        while pos + 8 <= size and len(out) < 64:
            fh.seek(pos)
            hdr = fh.read(16)
            n, kind = struct.unpack(">I4s", hdr[:8])
            if n == 1:
                n = struct.unpack(">Q", hdr[8:16])[0]
            elif n == 0:
                n = size - pos
            out.append(kind.decode("latin-1"))
            if n < 8:
                break
            pos += n
    return out


def analyse(path):
    """One decode pass: blackdetect + freezedetect on video, ebur128 on audio."""
    b, f = tv("blackDetect"), tv("freezeDetect")
    vf = (f"blackdetect=d={b['d']}:pix_th={b['pix_th']}:pic_th={b['pic_th']},"
          f"freezedetect=n={f['noise']}:d={f['d']}")
    p = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf", vf,
            "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"])
    err = p.stderr.decode(errors="replace")
    blacks = [(float(a), float(c)) for a, c in re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", err)]
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", err)]
    freezes = [(s, ends[k] if k < len(ends) else None) for k, s in enumerate(starts)]
    summ = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    num = lambda pat: (lambda m: float(m.group(1)) if m else None)(re.search(pat, summ))
    loud = {"I": num(r"I:\s*(-?[\d.]+|-inf)\s*LUFS"), "LRA": num(r"LRA:\s*(-?[\d.]+)\s*LU\b"),
            "TP": num(r"True peak:\s*Peak:\s*(-?[\d.]+|-inf)\s*dBFS")}
    return blacks, freezes, loud


def frame0_luma(path):
    p = sh(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1",
            "-vf", "scale=270:480:out_range=full,format=gray", "-f", "rawvideo", "-"])
    data = p.stdout
    return sum(data) / len(data) if data else None


def rms_spread(path):
    w = tv("voiceBedSpread")
    p = sh(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-acodec", "pcm_s16le", "-"])
    a = array.array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    n = int(48000 * w["window"])
    dbs, silent = [], 0
    for i in range(0, len(a) - n + 1, n):
        seg = a[i:i + n]
        ms = sum(x * x for x in seg) / n
        db = 10 * math.log10(ms / (32768.0 ** 2)) if ms > 0 else -120.0
        if db < w["silenceFloorDb"]:
            silent += 1
        else:
            dbs.append(db)
    if len(dbs) < 10:
        return None, None, None, silent
    dbs.sort()
    pct = lambda q: dbs[min(len(dbs) - 1, int(round(q * (len(dbs) - 1))))]
    return pct(0.9) - pct(0.1), pct(0.1), pct(0.9), silent

# ---------------------------------------------------------------- checks

def check(path, project=None, profile="both"):
    R = Results()
    info = probe(path)
    fm, du = tv("film"), tv("duration")
    vs = [s for s in info["streams"] if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    as_ = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    dur = float(info["format"].get("duration") or 0)
    if len(vs) != 1:
        R.add("container.streams", "fail", f"{len(vs)}v/{len(as_)}a", "1v/1a", "need exactly one video stream")
        return R, {"duration": dur}
    v = vs[0]
    vdur = float(v.get("duration") or dur)
    wh = f"{v.get('width')}x{v.get('height')}"
    R.add("container.size", "pass" if (v.get("width"), v.get("height")) == (fm["width"], fm["height"]) else "fail",
          wh, f"{fm['width']}x{fm['height']}")
    fps = rate(v.get("avg_frame_rate")) or rate(v.get("r_frame_rate"))
    R.add("container.fps", "pass" if any(abs(fps - x) <= fm["fpsTolerance"] for x in fm["fps"]) else "fail",
          f"{fps:.3f}", " or ".join(map(str, fm["fps"])))
    R.add("container.vcodec", "pass" if v.get("codec_name") == fm["vcodec"] else "fail", v.get("codec_name"), fm["vcodec"])
    R.add("container.pix_fmt", "pass" if v.get("pix_fmt") == fm["pixFmt"] else "fail", v.get("pix_fmt"), fm["pixFmt"])
    if v.get("color_range") == "pc":
        R.add("container.range", "warn", "pc", "tv", "full-range video; platforms expect tv range")
    if len(as_) != 1:
        R.add("container.audio", "fail", f"{len(as_)} streams", "1 AAC stream")
    else:
        a = as_[0]
        R.add("container.acodec", "pass" if a.get("codec_name") == fm["acodec"] else "fail", a.get("codec_name"), fm["acodec"])
        sr = int(a.get("sample_rate") or 0)
        R.add("container.sample_rate", "pass" if sr == fm["sampleRate"] else "fail", sr, fm["sampleRate"])
        ch = a.get("channels")
        R.add("container.channels", "pass" if ch == fm["channels"] else "warn", ch, fm["channels"])
        adur, ast = float(a.get("duration") or dur), float(a.get("start_time") or 0)
        gap = max(abs(adur + ast - vdur), ast)
        R.add("container.av_cover", "pass" if gap <= fm["avTolerance"] else "fail", f"{gap:.3f}s",
              f"<= {fm['avTolerance']}s", f"audio {ast:.2f}-{ast + adur:.2f}s, video {vdur:.2f}s")
    order = atom_order(path)
    if "moov" in order and "mdat" in order:
        fast = order.index("moov") < order.index("mdat")
        R.add("container.faststart", "pass" if fast else "warn", "moov first" if fast else "moov last", "moov first",
              "" if fast else "re-mux with: ffmpeg -i in.mp4 -c copy -movflags +faststart out.mp4")

    hard = du["hardMax"][profile]
    st = "fail" if dur > hard else ("pass" if du["warnMin"] <= dur <= du["warnMax"] else "warn")
    R.add("duration", st, f"{dur:.2f}s", f"{du['warnMin']}-{du['warnMax']}s, <= {hard}s ({profile})")

    last_word = None
    tl = os.path.join(project, "timeline.json") if project else None
    if tl and os.path.isfile(tl):
        with open(tl) as fh:
            T = json.load(fh)
        ends = [w["end"] for w in T.get("words", []) if "end" in w]
        if ends:
            last_word = max(ends)
            hold = dur - last_word
            R.add("final_hold", "pass" if hold >= tv("finalHold") else "fail", f"{hold:.2f}s", f">= {tv('finalHold')}s",
                  f"last word ends {last_word:.2f}s")
        if T.get("total") and abs(T["total"] - dur) > fm["avTolerance"]:
            R.add("timeline_total", "warn", f"{T['total']:.2f}s", f"{dur:.2f}s", "timeline.json total differs from the film")
    else:
        R.add("final_hold", "skip", None, None, "no timeline.json (pass --project)")

    luma = frame0_luma(path)
    R.add("frame0_luma", "pass" if luma is not None and luma > tv("frame0MinLuma") else "fail",
          None if luma is None else f"{luma:.1f}", f"> {tv('frame0MinLuma')}")

    blacks, freezes, loud = analyse(path)
    grace = tv("blackDetect")["endGrace"]
    mid = [(s, e) for s, e in blacks if s > 0.05 and e < dur - grace]
    tail = [(s, e) for s, e in blacks if e >= dur - grace and s > 0.05]
    head = [(s, e) for s, e in blacks if s <= 0.05]
    fmt = lambda segs: ", ".join(f"{s:.2f}-{e:.2f}" for s, e in segs)
    R.add("black.mid_film", "fail" if mid else "pass", len(mid), 0, fmt(mid))
    if head:
        R.add("black.opening", "fail", fmt(head), "none", "film opens on black")
    if tail:
        R.add("black.ending", "warn", fmt(tail), "none", "ends on black (fine if it is a deliberate fade)")

    hold_from = last_word if last_word is not None else dur - 4.0
    fz = [(s, e if e is not None else dur) for s, e in freezes]
    body = [(s, min(e, hold_from)) for s, e in fz if s < hold_from and min(e, hold_from) - s > tv("freezeDetect")["d"]]
    total = sum(e - s for s, e in body)
    per30 = total / max(dur / 30.0, 1e-9)
    lim = tv("freezeDetect")["maxPer30s"]
    R.add("frozen", "warn" if body or per30 > lim else "pass", f"{total:.2f}s",
          f"none > {tv('freezeDetect')['d']}s, <= {lim}s/30s",
          (fmt(body) + (" (hold excluded" + (" from timeline)" if last_word is not None else ", assumed last 4 s)"))) if body
          else ("hold excluded" if fz else ""))

    L = tv("loudness")
    if loud["I"] is None:
        R.add("loudness.integrated", "fail", None, f"{L['integrated']} +-{L['tolerance']}", "ebur128 gave no reading")
    else:
        R.add("loudness.integrated", "pass" if abs(loud["I"] - L["integrated"]) <= L["tolerance"] else "fail",
              f"{loud['I']:.1f} LUFS", f"{L['integrated']} +-{L['tolerance']}")
    if loud["TP"] is not None:
        R.add("loudness.true_peak", "pass" if loud["TP"] <= L["truePeakMax"] else "fail", f"{loud['TP']:.1f} dBTP",
              f"<= {L['truePeakMax']}")
    if loud["LRA"] is not None:
        R.add("loudness.lra", "info", f"{loud['LRA']:.1f} LU")

    spread, p10, p90, silent = rms_spread(path)
    w = tv("voiceBedSpread")
    if spread is None:
        R.add("voice_bed_spread", "skip", None, None, "too little audio above the silence floor")
    else:
        R.add("voice_bed_spread", "pass" if spread >= w["minSpreadDb"] else "warn", f"{spread:.1f} dB",
              f">= {w['minSpreadDb']}", f"P10 {p10:.1f} / P90 {p90:.1f} dBFS, {silent} silent windows dropped")
    return R, {"duration": dur, "last_word": last_word, "loudness": loud}

# ---------------------------------------------------------------- PNG + contact sheet

def write_png(path, w, h, rows, alpha):
    """rows: list of bytes, each w*(4 if alpha else 3) long."""
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if alpha else 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def safe_zone_overlay(path, profile, W=1080, H=1920):
    z = tv("safeZones")[profile]
    panel = tv("safeZones")["panelWidth"]
    red, clear, dash = bytes((255, 0, 0, 96)), bytes(4), bytes((0, 235, 255, 235))
    x0, x1 = (W - panel) // 2, (W - panel) // 2 + panel
    y0, y1 = z["top"], z["bottom"]
    th, on, off = 6, 28, 18
    full_red = red * W
    right = clear * z["rightX"] + red * (W - z["rightX"])
    rows = []
    for y in range(H):
        if y < z["top"] or y > z["bottom"]:
            r = bytearray(full_red)
        elif y >= z["rightFromY"]:
            r = bytearray(right)
        else:
            r = bytearray(clear * W)
        if y0 <= y < y0 + th or y1 - th <= y < y1:
            for x in range(x0, x1):
                if (x - x0) % (on + off) < on:
                    r[4 * x:4 * x + 4] = dash
        if y0 <= y < y1 and (y - y0) % (on + off) < on:
            for x in list(range(x0, x0 + th)) + list(range(x1 - th, x1)):
                r[4 * x:4 * x + 4] = dash
        rows.append(r)
    write_png(path, W, H, rows, True)


FONT = {  # 3x5 bitmap glyphs, rows top->bottom
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    ".": ["000", "000", "000", "000", "010"], "s": ["000", "111", "100", "011", "110"],
    "E": ["111", "100", "111", "100", "111"], "N": ["101", "111", "111", "111", "101"],
    "D": ["110", "101", "101", "101", "110"], " ": ["000"] * 5,
}


def draw_label(buf, stride, x, y, text, scale=3):
    w = (4 * len(text) + 1) * scale
    h = 7 * scale
    for yy in range(y, y + h):
        buf[yy * stride + 3 * x: yy * stride + 3 * (x + w)] = b"\x00" * (3 * w)
    for k, ch in enumerate(text):
        g = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(g):
            for gx, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        py = y + (gy + 1) * scale + dy
                        px = x + ((4 * k + 1) + gx) * scale
                        buf[py * stride + 3 * px: py * stride + 3 * (px + scale)] = b"\xff" * (3 * scale)


def frames_with_overlay(video, overlay, vw, vh, tw, th, args_in, vf_head):
    fc = f"[1:v]scale={vw}:{vh}[o];[0:v]{vf_head}[v];[v][o]overlay=0:0:format=auto,scale={tw}:{th}:flags=area,format=rgb24"
    p = sh(["ffmpeg", "-v", "error"] + args_in + ["-i", video, "-i", overlay, "-filter_complex", fc,
                                                  "-f", "rawvideo", "-"])
    n = tw * th * 3
    return [p.stdout[i:i + n] for i in range(0, len(p.stdout) - n + 1, n)]


def contact_sheet(video, out, profile, dur, vw, vh, step=None, tw=270, th=480, cols=7, pad=8):
    step = step or tv("sheetStep")
    with tempfile.TemporaryDirectory() as tmp:
        ov = os.path.join(tmp, "overlay.png")
        safe_zone_overlay(ov, profile)
        frames = frames_with_overlay(video, ov, vw, vh, tw, th, [], f"fps=1/{step}")
        labels = [f"{k * step:.0f}s" for k in range(len(frames))]
        last = frames_with_overlay(video, ov, vw, vh, tw, th, ["-sseof", "-0.1"], "null")
        if last:
            frames.append(last[-1])
            labels.append("END")
    if not frames:
        raise RuntimeError("no frames decoded for the sheet")
    rows_n = math.ceil(len(frames) / cols)
    W, H = cols * tw + (cols + 1) * pad, rows_n * th + (rows_n + 1) * pad
    stride = 3 * W
    buf = bytearray(b"\x28" * (stride * H))
    for k, fr in enumerate(frames):
        cx, cy = pad + (k % cols) * (tw + pad), pad + (k // cols) * (th + pad)
        for y in range(th):
            buf[(cy + y) * stride + 3 * cx:(cy + y) * stride + 3 * (cx + tw)] = fr[y * tw * 3:(y + 1) * tw * 3]
        draw_label(buf, stride, cx + 4, cy + 4, labels[k])
    write_png(out, W, H, [buf[y * stride:(y + 1) * stride] for y in range(H)], False)
    return len(frames)

# ---------------------------------------------------------------- self-test

def self_test():
    ok = True

    def expect(R, name, status):
        nonlocal ok
        got = next((i["status"] for i in R.items if i["check"] == name), "missing")
        good = got == status
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL'}  {name:22s} expected {status:5s} got {got}")

    with tempfile.TemporaryDirectory() as tmp:
        good, bad = os.path.join(tmp, "good.mp4"), os.path.join(tmp, "bad.mp4")
        enc = ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac"]
        sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=6",
            "-f", "lavfi", "-i", "sine=f=1000:sample_rate=48000:d=6", "-af", "volume=7dB", "-ac", "2", "-ar", "48000"]
           + enc + [good], check=True)
        fc = ("color=black:s=720x1280:r=25:d=0.6[a];testsrc2=s=720x1280:r=25:d=1.4[b];color=black:s=720x1280:r=25:d=1[c];"
              "color=red:s=720x1280:r=25:d=2.5[d];testsrc2=s=720x1280:r=25:d=0.5[e];[a][b][c][d][e]concat=n=5:v=1:a=0[v]")
        sh(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-f", "lavfi", "-i", "sine=f=440:sample_rate=44100:d=4",
            "-map", "[v]", "-map", "0:a", "-af", "volume=17dB", "-ac", "1"] + enc + [bad], check=True)
        pg, pb = os.path.join(tmp, "pg"), os.path.join(tmp, "pb")
        for d, last in ((pg, 3.5), (pb, 5.5)):
            os.makedirs(d)
            with open(os.path.join(d, "timeline.json"), "w") as fh:
                json.dump({"total": 6, "scenes": [], "words": [{"scene": "a", "i": 0, "text": "x", "start": 0.2, "end": last}]}, fh)
        print("-- good clip (1080x1920 h264/aac 48k, moving test pattern, steady tone)")
        R, _ = check(good, pg)
        for n, s in [("container.size", "pass"), ("container.fps", "pass"), ("container.pix_fmt", "pass"),
                     ("container.sample_rate", "pass"), ("container.av_cover", "pass"), ("duration", "warn"),
                     ("final_hold", "pass"), ("frame0_luma", "pass"), ("black.mid_film", "pass"),
                     ("loudness.integrated", "pass"), ("loudness.true_peak", "pass"), ("voice_bed_spread", "warn")]:
            expect(R, n, s)
        print("-- bad clip (720x1280 25 fps, black open + mid black, frozen red, short loud 44.1k mono audio)")
        R, _ = check(bad, pb)
        for n, s in [("container.size", "fail"), ("container.fps", "fail"), ("container.sample_rate", "fail"),
                     ("container.channels", "warn"), ("container.av_cover", "fail"), ("final_hold", "fail"),
                     ("frame0_luma", "fail"), ("black.opening", "fail"), ("black.mid_film", "fail"), ("frozen", "warn"),
                     ("loudness.true_peak", "fail")]:
            expect(R, n, s)
        sheet = os.path.join(tmp, "sheet.png")
        n = contact_sheet(good, sheet, "both", 6, 1080, 1920, step=2)
        with open(sheet, "rb") as fh:
            sig = fh.read(8)
        good_sheet = sig == b"\x89PNG\r\n\x1a\n" and n == 4
        ok = ok and good_sheet
        print(f"{'PASS' if good_sheet else 'FAIL'}  contact sheet         {n} tiles, png={sig[:4] == b'\x89PNG'}")
    print("self-test", "OK" if ok else "FAILED")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Measured QA of the final MP4.")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--project", help="project root (for timeline.json)")
    ap.add_argument("--profile", choices=["tiktok", "reels", "both"], default="both")
    ap.add_argument("--sheet", metavar="OUT.png", help="write a contact sheet with the safe-zone overlay")
    ap.add_argument("--json", nargs="?", const="-", metavar="OUT.json", help="JSON summary to stdout (or a file)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if not a.video:
        ap.error("video is required")
    R, meta = check(a.video, a.project, a.profile)
    if a.sheet:
        info = probe(a.video)
        v = next(s for s in info["streams"] if s.get("codec_type") == "video")
        n = contact_sheet(a.video, a.sheet, a.profile, meta["duration"], v["width"], v["height"])
        R.add("sheet", "info", f"{n} frames", None, a.sheet)
    summary = {"file": os.path.abspath(a.video), "profile": a.profile, "checks": R.items,
               "failures": R.n("fail"), "warnings": R.n("warn"), "ok": R.n("fail") == 0}
    if a.json == "-":
        print(json.dumps(summary, indent=1))
    else:
        R.print()
        print(f"\n{R.n('fail')} hard failures, {R.n('warn')} warnings ({a.profile} profile). "
              "Measured only: nobody looked at text size/overlap or listened to the mix.")
        if a.json:
            with open(a.json, "w") as fh:
                json.dump(summary, fh, indent=1)
    sys.exit(1 if R.n("fail") else 0)


if __name__ == "__main__":
    main()
