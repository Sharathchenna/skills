#!/usr/bin/env python3
"""Fact ledger validator + script lint for SCRIPT.json. Run from the project root (or pass --project).

  python3 -I tools/check_facts.py [--project DIR] [--strict] [--credits OUT_DIR]
  python3 -I tools/check_facts.py --self-test

Reads   DIR/SCRIPT.json          [{id, text, facts?:[fact ids], onscreen?:[strings]}]  or  {"mode": "news"|"cs", "scenes": [...]}
        DIR/facts/FACTS.json     [{id "f-0001", claim, value?, quote?, location?, status, sources:[ids], caveat?, checkedAt,
                                   asOf?, who_measured?, evidence?, spokenAs?, mustPreempt?}]
        DIR/facts/SOURCES.json   [{id "s-0001", title, url, publisher, accessed, tier?, kind?, licence?, attribution?,
                                   role?, saved?, modified?}]
        DIR/timeline.json        (optional; real narration durations for the fact-density check)
        thresholds.json          (next to this script: every number and phrase list used here)

Checks  ledger    ids, duplicates, required fields, dates, statuses, licences, source links, tiers
        links     every scene (except end/share) cites facts that exist; unverified -> error; contested needs a caveat;
                  illustrative needs an on-frame 'illustrative' tag; news mode: asOf on present-tense facts
        numbers   every number in narration AND onscreen strings matches a number in the cited facts'
                  value/claim/quote/spokenAs or their sources' title/url/saved text (+-3%, years exact; spoken numbers parsed)
        style     banned marks, banned phrases, intensifier budget, sentence length, pronoun scene openers,
                  parallel runs, repeated openers, dates per scene/video
        density   seconds of narration per fact-bearing sentence
Prints one line per finding:  LEVEL  rule  [thresholds key]  where: message.   Exit 1 on any error.
--strict turns warnings into errors. --credits OUT writes OUT/pinned-comment.txt and OUT/caption-draft.txt.

Fact-ledger design, TTS punctuation rules and phrase lists adapted from shorts-kit by howznguyen (MIT),
https://github.com/howznguyen/shorts-kit.
"""
import argparse, datetime as dt, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- thresholds

def load_thresholds(path=None):
    path = path or os.path.join(HERE, "thresholds.json")
    with open(path) as fh:
        return json.load(fh)

TH = load_thresholds()

def tv(key):
    return TH[key]["value"]

def tlevel(key, default="warn"):
    return TH.get(key, {}).get("level", default)

# ---------------------------------------------------------------- reporting

class Report:
    def __init__(self):
        self.items = []          # (level, rule, key, where, msg)

    def add(self, level, rule, key, where, msg):
        self.items.append((level, rule, key, where, msg))

    def err(self, rule, key, where, msg):
        self.add("error", rule, key, where, msg)

    def warn(self, rule, key, where, msg):
        self.add("warn", rule, key, where, msg)

    def by(self, key, rule, where, msg):
        """Level taken from thresholds.json[key].level."""
        self.add(tlevel(key), rule, key, where, msg)

    def strictify(self):
        self.items = [("error",) + i[1:] if i[0] == "warn" else i for i in self.items]

    def count(self, level):
        return sum(1 for i in self.items if i[0] == level)

    def rules(self, level=None):
        return {i[1] for i in self.items if level is None or i[0] == level}

    def print(self, out=sys.stdout):
        order = {"error": 0, "warn": 1, "info": 2}
        for level, rule, key, where, msg in sorted(self.items, key=lambda i: order[i[0]]):
            k = f"[{key}]" if key else ""
            print(f"{level.upper():5s}  {rule:28s} {k:24s} {where}: {msg}", file=out)

# ---------------------------------------------------------------- numbers (digits and spoken)

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
DENOM = {"half": 2, "halves": 2, "third": 3, "thirds": 3, "quarter": 4, "quarters": 4, "fifth": 5, "fifths": 5,
         "sixth": 6, "sixths": 6, "seventh": 7, "sevenths": 7, "eighth": 8, "eighths": 8, "ninth": 9, "ninths": 9,
         "tenth": 10, "tenths": 10, "hundredth": 100, "hundredths": 100, "thousandth": 1000, "thousandths": 1000}
MULTW = {"twice": 2, "thrice": 3, "double": 2, "doubled": 2, "doubles": 2, "triple": 3, "tripled": 3, "triples": 3,
         "quadruple": 4, "quadrupled": 4}
DIGIT_SUFFIX = {"k": 1e3, "K": 1e3, "M": 1e6, "B": 1e9, "bn": 1e9, "T": 1e12,
                "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}

DIGIT_RE = re.compile(
    r"(?<![A-Za-z0-9.\-])[$€£]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
    r"(?:\s?(%|percent\b|per cent\b|x\b|×|times\b|k\b|K\b|M\b|B\b|bn\b|T\b|thousand\b|million\b|billion\b|trillion\b|s\b))?"
    r"(?![A-Za-z0-9])")
WORD_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")


class Num:
    __slots__ = ("value", "percent", "kind", "raw", "start", "end", "bare")

    def __init__(self, value, raw, start, end, percent=False, kind="number", bare=False):
        self.value, self.raw, self.start, self.end = float(value), raw, start, end
        self.percent, self.kind, self.bare = percent, kind, bare      # kind: number|year|fraction|multiplier

    def label(self):
        v = self.value
        s = (f"{int(v)}" if self.kind == "year" else f"{int(v):,}") if v == int(v) else f"{v:.10g}"
        return s + ("%" if self.percent else "") + ("x" if self.kind == "multiplier" else "")

    def forms(self):
        """Equivalent values: percent <-> fraction."""
        v = self.value
        out = {v}
        if self.percent:
            out.add(v / 100)
        elif self.kind == "fraction" or 0 < v <= 1:
            out.add(v * 100)
        return out

    def __repr__(self):
        return f"Num({self.raw!r}={self.label()},{self.kind})"


def _spoken_at(words, i):
    """Parse a spoken number starting at words[i]. words: [(lower, start, end)]. Returns (Num-args, next_i) or None."""
    n = len(words)
    w = lambda k: words[k][0] if k < n else ""
    j = i
    parts_used = []
    # standalone multipliers
    if w(j) in MULTW:
        return dict(value=MULTW[w(j)], kind="multiplier"), j + 1
    if w(j) == "half":
        return dict(value=0.5, kind="fraction"), j + 1
    lead_a = w(j) in ("a", "an")
    if lead_a:
        if w(j + 1) in SCALES or w(j + 1) == "dozen":
            total, current, j = 0, 1, j + 1
        elif w(j + 1) in DENOM and w(j + 1) not in ("hundredth", "thousandth"):
            return dict(value=1 / DENOM[w(j + 1)], kind="fraction"), j + 2
        else:
            return None
    else:
        total, current = 0, None

    def unit_value(tok):
        if tok in UNITS:
            return UNITS[tok]
        if tok in TENS:
            return TENS[tok]
        if "-" in tok:
            a, _, b = tok.partition("-")
            if a in TENS and b in UNITS and 0 < UNITS[b] < 10:
                return TENS[a] + UNITS[b]
        return None

    saw_number = lead_a
    while j < n:
        tok = w(j)
        uv = unit_value(tok)
        if uv is not None:
            if current is not None and current % 100 != 0 and current >= 10 and uv < 10 and current % 10 == 0:
                current += uv                     # "twenty one"
            elif current is not None and current % 100 == 0 and current > 0:
                current += uv                     # "three hundred five"
            elif current is not None and current != 0 and not lead_a:
                break                             # "one two" -> stop (two numbers)
            else:
                current = (current or 0) + uv if current else uv
            saw_number, j = True, j + 1
            parts_used.append(tok)
            continue
        if tok in SCALES and saw_number:
            c = 1 if current is None else current
            if tok == "hundred":
                current = c * 100
            else:
                total += c * SCALES[tok]
                current = 0
            j += 1
            parts_used.append(tok)
            continue
        if tok == "dozen" and saw_number:
            current = (1 if current is None else current) * 12
            j += 1
            continue
        if tok == "and" and saw_number and unit_value(w(j + 1)) is not None and (current or 0) % 100 == 0 and (total or current):
            j += 1                                # "three hundred and twenty"
            continue
        break
    if not saw_number:
        return None
    value = total + (current or 0)
    kind, percent, bare = "number", False, False
    # decimals: "one point five"
    if w(j) == "point" and w(j + 1) in UNITS and UNITS[w(j + 1)] < 10:
        digits, k = "", j + 1
        while k < n and w(k) in UNITS and UNITS[w(k)] < 10:
            digits += str(UNITS[w(k)])
            k += 1
        value = float(f"{int(value)}.{digits}")
        j, parts_used = k, parts_used + ["point"]
        if w(j) in SCALES and w(j) != "hundred":
            value *= SCALES[w(j)]
            j += 1
    # "one and a half"
    if w(j) == "and" and w(j + 1) == "a" and w(j + 2) == "half":
        value += 0.5
        j, parts_used = j + 3, parts_used + ["half"]
    # fractions: "two thirds", "a fifth" (handled above), "one quarter"
    if w(j) in DENOM and value and value < 100 and not lead_a and w(j) not in ("hundredth", "thousandth") \
            and (w(j).endswith("s") or value == 1):
        return dict(value=value / DENOM[w(j)], kind="fraction"), j + 1
    if w(j) == "percent":
        percent, j = True, j + 1
    elif w(j) == "per" and w(j + 1) == "cent":
        percent, j = True, j + 2
    elif w(j) == "times":
        kind, j = "multiplier", j + 1
    if not percent and kind == "number" and not lead_a and all(p in tv("ignoreBareNumberWords") for p in parts_used):
        bare = True
    return dict(value=value, kind=kind, percent=percent, bare=bare), j


def parse_numbers(text):
    """Every number in text, digits and spoken, as Num objects with character spans."""
    text = text.replace("’", "'")
    nums, masked = [], list(text)
    for m in DIGIT_RE.finditer(text):
        ip, dec, suf = m.group(1), m.group(2) or "", (m.group(3) or "").strip()
        value = float(ip.replace(",", "") + dec)
        percent = suf in ("%", "percent", "per cent")
        kind = "multiplier" if suf in ("x", "×", "times") else "number"
        if suf in DIGIT_SUFFIX:
            value *= DIGIT_SUFFIX[suf]
        if not dec and "," not in ip and (suf in ("", "s")) and 1000 <= value <= 2100:
            kind = "year"
        nums.append(Num(value, m.group(0), m.start(), m.end(), percent=percent, kind=kind))
        for k in range(m.start(), m.end()):
            masked[k] = " "
    masked = "".join(masked)
    words = [(m.group(0).lower(), m.start(), m.end()) for m in WORD_RE.finditer(masked)]
    i = 0
    while i < len(words):
        got = _spoken_at(words, i)
        if got:
            args, j = got
            s, e = words[i][1], words[j - 1][2]
            nums.append(Num(raw=text[s:e], start=s, end=e, **args))
            i = j
        else:
            i += 1
    nums.sort(key=lambda x: x.start)
    return nums


def checkable(nums):
    return [x for x in nums if not x.bare]


def num_match(a, b, tol):
    if a.kind == "year" or b.kind == "year":
        return a.value == b.value
    for x in a.forms():
        for y in b.forms():
            if x == y or (max(abs(x), abs(y)) > 0 and abs(x - y) <= tol * max(abs(x), abs(y))):
                return True
    return False


def canonical_words(text):
    """Lowercase word list with every number replaced by one canonical token (for WER)."""
    text = text.replace("’", "'")
    out, pos = [], 0
    for x in parse_numbers(text):
        out += re.findall(r"[a-z0-9']+", text[pos:x.start].lower().replace("-", " "))
        out.append(f"<{x.label()}>")
        pos = x.end
    out += re.findall(r"[a-z0-9']+", text[pos:].lower().replace("-", " "))
    return out

# ---------------------------------------------------------------- text helpers

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])[\"”')\]]*\s+", text.strip()) if s.strip()]


def word_count(sentence):
    """Words in a sentence, a spoken number counting as one."""
    s, pos, parts = sentence.replace("’", "'"), 0, []
    for x in parse_numbers(s):
        parts.append(s[pos:x.start])
        parts.append(" N ")
        pos = x.end
    parts.append(s[pos:])
    return len(re.findall(r"[\w'][\w'\-]*", "".join(parts)))


def first_word(s):
    m = re.search(r"[A-Za-z0-9][\w'’]*", s)
    return m.group(0).lower().replace("’", "'") if m else ""


def phrase_re(p):
    p = p.replace("’", "'")
    return re.compile(r"(?<![\w])" + r"\s+".join(map(re.escape, p.split())) + r"(?![\w])", re.I)


def snippet(text, i, j, pad=22):
    a, b = max(0, i - pad), min(len(text), j + pad)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FID, SID = re.compile(r"^f-\d{4,}$"), re.compile(r"^s-\d{4,}$")


def parse_date(s):
    if not isinstance(s, str) or not DATE_RE.match(s):
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None

# ---------------------------------------------------------------- loading

def load_json(path, rep, rule, what):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        rep.err(rule, "", what, f"missing {path}")
    except json.JSONDecodeError as e:
        rep.err(rule, "", what, f"{path} is not valid JSON ({e})")
    return None


def load_script(path, rep):
    data = load_json(path, rep, "script.unreadable", "SCRIPT.json")
    if data is None:
        return None, []
    mode = None
    if isinstance(data, dict):
        mode, data = data.get("mode"), data.get("scenes")
        if mode not in (None, "news", "cs"):
            rep.err("script.bad-mode", "", "SCRIPT.json", f"mode must be 'news' or 'cs', got {mode!r}")
    if not isinstance(data, list):
        rep.err("script.not-array", "", "SCRIPT.json", "expected an array of scenes or {mode, scenes:[...]}")
        return mode, []
    seen, scenes = set(), []
    for k, sc in enumerate(data):
        where = f"scene #{k + 1}"
        if not isinstance(sc, dict) or not isinstance(sc.get("id"), str) or not isinstance(sc.get("text"), str):
            rep.err("script.bad-scene", "", where, "each scene needs string 'id' and 'text'")
            continue
        if sc["id"] in seen:
            rep.err("script.duplicate-id", "", f"scene {sc['id']}", "duplicate scene id")
        seen.add(sc["id"])
        for key in ("facts", "onscreen"):
            v = sc.get(key, [])
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                rep.err("script.bad-field", "", f"scene {sc['id']}", f"'{key}' must be a list of strings")
                sc = dict(sc, **{key: []})
        scenes.append(sc)
    return mode, scenes

# ---------------------------------------------------------------- ledger

def validate_ledger(facts, sources, rep, project):
    today = dt.date.today()
    src = {}
    if not isinstance(sources, list):
        rep.err("ledger.not-array", "", "SOURCES.json", "must be a JSON array")
        sources = []
    if not isinstance(facts, list):
        rep.err("ledger.not-array", "", "FACTS.json", "must be a JSON array")
        facts = []
    for s in sources:
        if not isinstance(s, dict):
            rep.err("ledger.bad-record", "", "SOURCES.json", f"not an object: {s!r:.60}")
            continue
        sid = s.get("id")
        at = f"source {sid}"
        if not isinstance(sid, str) or not SID.match(sid):
            rep.err("ledger.bad-id", "", at, "id must look like s-0001")
        if sid in src:
            rep.err("ledger.duplicate-id", "", at, "duplicate source id")
        src.setdefault(sid, s)
        for k in ("title", "publisher", "accessed"):
            if not s.get(k):
                rep.err("ledger.missing-field", "", at, f"missing {k}")
        if s.get("accessed") and not parse_date(s["accessed"]):
            rep.err("ledger.bad-date", "", at, f"accessed {s['accessed']!r} is not YYYY-MM-DD")
        lic = str(s.get("licence", "")).lower()
        if not s.get("url") and not lic.startswith("own"):
            rep.warn("ledger.no-url", "", at, "no url (only own recordings may omit it)")
        kind = s.get("kind")
        if kind is not None and kind not in tv("sourceKinds"):
            rep.err("ledger.bad-kind", "sourceKinds", at, f"kind {kind!r} not in {tv('sourceKinds')}")
        if kind in tv("assetKinds"):
            if not s.get("licence"):
                rep.err("ledger.asset-no-licence", "assetKinds", at, f"{kind} source needs a licence")
            if not s.get("attribution"):
                rep.warn("ledger.asset-no-attribution", "assetKinds", at,
                         "no verbatim 'attribution'; credits will use a generated fallback")
        if "tier" in s and s["tier"] not in (1, 2, 3):
            rep.err("ledger.bad-tier", "", at, f"tier must be 1, 2 or 3, got {s['tier']!r}")
        if "role" in s and s["role"] not in tv("sourceRoles"):
            rep.err("ledger.bad-role", "sourceRoles", at, f"role {s['role']!r} not in {tv('sourceRoles')}")
        if s.get("saved"):
            p = os.path.join(project, s["saved"])
            if not os.path.isfile(p):
                rep.warn("ledger.saved-missing", "", at, f"saved text {s['saved']} not found (number backing skips it)")
    fx = {}
    for f in facts:
        if not isinstance(f, dict):
            rep.err("ledger.bad-record", "", "FACTS.json", f"not an object: {f!r:.60}")
            continue
        fid = f.get("id")
        at = f"fact {fid}"
        if not isinstance(fid, str) or not FID.match(fid):
            rep.err("ledger.bad-id", "", at, "id must look like f-0001")
        if fid in fx:
            rep.err("ledger.duplicate-id", "", at, "duplicate fact id")
        fx.setdefault(fid, f)
        if not f.get("claim"):
            rep.err("ledger.missing-field", "", at, "missing claim")
        st = f.get("status")
        if st not in tv("factStatuses"):
            rep.err("ledger.bad-status", "factStatuses", at, f"status {st!r} not in {tv('factStatuses')}")
        d = parse_date(f.get("checkedAt"))
        if not d:
            rep.err("ledger.bad-date", "", at, "checkedAt missing or not YYYY-MM-DD")
        elif d > today:
            rep.warn("ledger.future-date", "", at, f"checkedAt {d} is in the future")
        if "asOf" in f and not parse_date(f["asOf"]):
            rep.err("ledger.bad-date", "", at, f"asOf {f['asOf']!r} is not YYYY-MM-DD")
        srcs = f.get("sources", [])
        if not isinstance(srcs, list):
            rep.err("ledger.bad-field", "", at, "sources must be a list of source ids")
            srcs = []
        if st == "verified" and not srcs:
            rep.err("ledger.verified-no-source", "", at, "verified with no sources")
        for sid in srcs:
            if sid not in src:
                rep.err("ledger.missing-source", "", at, f"cites {sid}, not in SOURCES.json")
            elif src[sid].get("role") == "rejected":
                rep.err("ledger.rejected-source", "sourceRoles", at, f"cites {sid}, which is marked rejected")
        if st == "contested" and not f.get("caveat"):
            rep.warn("ledger.contested-no-caveat", "", at, "contested with no caveat (cannot be used in a script)")
        tiers = [src[s]["tier"] for s in srcs if s in src and src[s].get("tier") in (1, 2, 3)]
        if tiers and min(tiers) >= tv("tier3Warn"):
            rep.by("tier3Warn", "ledger.weak-tier", at, f"best source is tier {min(tiers)}")
        if srcs and all(src.get(s, {}).get("role") == "candidate-finder" for s in srcs):
            rep.warn("ledger.candidate-finder-only", "sourceRoles", at, "only candidate-finder sources")
        if "evidence" in f and f["evidence"] not in tv("evidenceGrades"):
            rep.warn("ledger.bad-evidence", "evidenceGrades", at, f"evidence {f['evidence']!r} unknown")
        if "who_measured" in f and f["who_measured"] not in tv("whoMeasured"):
            rep.err("ledger.bad-who-measured", "whoMeasured", at, f"who_measured {f['who_measured']!r} not in {tv('whoMeasured')}")
    return fx, src

# ---------------------------------------------------------------- script lint

def backing_numbers(fact, src, project, cache):
    fid = fact.get("id")
    if fid in cache:
        return cache[fid]
    texts = [fact.get(k) for k in ("value", "claim", "quote")]
    sa = fact.get("spokenAs")
    texts += sa if isinstance(sa, list) else [sa]
    for sid in fact.get("sources", []) or []:
        texts += [src.get(sid, {}).get("title"), src.get(sid, {}).get("url")]   # ids such as arXiv:1706.03762
        p = src.get(sid, {}).get("saved")
        if p and os.path.isfile(os.path.join(project, p)):
            with open(os.path.join(project, p), errors="replace") as fh:
                texts.append(fh.read())
    nums = []
    for t in texts:
        if isinstance(t, (int, float)):
            t = str(t)
        if isinstance(t, str):
            nums += parse_numbers(t)
    cache[fid] = nums
    return nums


def lint_links(scenes, fx, src, rep, mode):
    exempt = set(tv("exemptSceneIds"))
    today = dt.date.today()
    present = [phrase_re(w) for w in tv("presentTenseWords")]
    tag = tv("illustrativeTag").lower()
    for sc in scenes:
        where = f"scene {sc['id']}"
        ids = sc.get("facts", [])
        if not ids and sc["id"] not in exempt:
            rep.warn("links.no-facts", "exemptSceneIds", where, "cites no fact (only end/share scenes may)")
        used = []
        for fid in ids:
            f = fx.get(fid)
            if not f:
                rep.err("links.unknown-fact", "", where, f"cites {fid}, not in FACTS.json")
                continue
            used.append(f)
            st = f.get("status")
            if st == "unverified":
                rep.err("links.unverified", "factStatuses", where, f"{fid} is unverified (verify it or cut the line)")
            elif st == "contested" and not f.get("caveat"):
                rep.err("links.contested-no-caveat", "factStatuses", where, f"{fid} is contested and has no caveat")
            elif st == "contested":
                rep.warn("links.contested", "factStatuses", where,
                         f"{fid} is contested; say the caveat on frame or in the caption: {f['caveat']}")
            elif st == "illustrative" and not any(tag in o.lower() for o in sc.get("onscreen", [])):
                rep.by("illustrativeTag", "links.illustrative-untagged", where,
                       f"{fid} is illustrative; draw an on-frame '{tag}' tag and list it in onscreen[]")
            if mode == "news" and st in ("verified", "contested"):
                claim = str(f.get("claim", ""))
                if not f.get("asOf") and any(p.search(claim) for p in present):
                    rep.err("links.news-no-asof", "presentTenseWords", where,
                            f"{fid} is a present-tense claim with no asOf date")
                d = parse_date(f.get("asOf"))
                if d and (today - d).days > tv("asOfMaxDays"):
                    rep.by("asOfMaxDays", "links.news-stale", where, f"{fid} asOf {d} is {(today - d).days} days old")
                if f.get("who_measured") == "vendor":
                    rep.warn("links.vendor-measured", "whoMeasured", where,
                             f"{fid} was measured by the vendor; say who ran it")
        graded = [f for f in used if f.get("evidence")]
        if graded and all(f["evidence"] in tv("weakEvidence") for f in graded):
            hits = [w for w in tv("universalWords") if phrase_re(w).search(sc["text"])]
            if hits:
                rep.by("universalWords", "links.weak-universal", where, f"weak evidence but says {hits}")


def lint_numbers(scenes, fx, src, rep, project):
    tol, cache = tv("numberTolerance"), {}
    cited_any = [fid for sc in scenes for fid in sc.get("facts", []) if fid in fx]
    for sc in scenes:
        ids = [fid for fid in sc.get("facts", []) if fid in fx]
        pool_ids = ids or sorted(set(cited_any)) or sorted(fx)
        pool = [(fid, n) for fid in pool_ids for n in backing_numbers(fx[fid], src, project, cache)]
        fields = [("narration", sc["text"])] + [(f"onscreen[{k}]", o) for k, o in enumerate(sc.get("onscreen", []))]
        for field, text in fields:
            for n in checkable(parse_numbers(text)):
                hit = next((fid for fid, c in pool if num_match(n, c, tol)), None)
                if hit is None:
                    scope = f"cited facts {ids}" if ids else "any cited fact (scene cites none)"
                    rep.err("numbers.unbacked", "numberTolerance", f"scene {sc['id']} {field}",
                            f"\"{n.raw}\" ({n.label()}) not found in {scope}")


def lint_style(scenes, rep):
    marks = tv("bannedMarks")
    phrases = [(p, phrase_re(p)) for p in tv("bannedPhrases")]
    intens = [(p, phrase_re(p)) for p in tv("intensifiers")]
    ignore = set(tv("openerIgnore"))
    all_sents, intens_hits, years_total = [], [], 0
    for sc in scenes:
        where, text = f"scene {sc['id']}", sc["text"].replace("’", "'")
        for mark in marks:
            low = text.lower()
            i = low.find(mark.lower())
            while i >= 0:
                j = i + len(mark)
                if not (mark == ":" and 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit()):
                    rep.by("bannedMarks", "style.banned-mark", where, f"{mark.strip() or mark!r} in \"{snippet(text, i, j)}\"")
                i = low.find(mark.lower(), j)
        for field, t in [("", text)] + [(" onscreen", o) for o in sc.get("onscreen", [])]:
            for p, rx in phrases:
                for m in rx.finditer(t):
                    rep.by("bannedPhrases", "style.banned-phrase", where + field, f"\"{p}\" in \"{snippet(t, m.start(), m.end())}\"")
        for p, rx in intens:
            intens_hits += [(sc["id"], p) for _ in rx.finditer(text)]
        fw = first_word(text)
        if fw in tv("pronounOpeners"):
            rep.by("pronounOpeners", "style.pronoun-opener", where, f"opens with \"{fw}\"; open with a name")
        years = [n for n in parse_numbers(text) if n.kind == "year"]
        years_total += len(years)
        if len(years) > tv("datesPerScene"):
            rep.by("datesPerScene", "style.dates-per-scene", where, f"{len(years)} years spoken: {[y.raw for y in years]}")
        for s in sentences(text):
            wc = word_count(s)
            if wc > tv("maxSentenceWords"):
                rep.by("maxSentenceWords", "style.long-sentence", where, f"{wc} words: \"{s[:60]}…\"")
            all_sents.append((sc["id"], first_word(s), s))
    if years_total > tv("datesPerVideo"):
        rep.by("datesPerVideo", "style.dates-per-video", "script", f"{years_total} years spoken")
    if len(intens_hits) > tv("intensifierBudget"):
        rep.by("intensifierBudget", "style.intensifiers", "script",
               f"{len(intens_hits)} intensifiers (budget {tv('intensifierBudget')}): {intens_hits}")
    run_n = tv("parallelRun")
    k = 0
    while k < len(all_sents):
        fw = all_sents[k][1]
        j = k
        while j + 1 < len(all_sents) and all_sents[j + 1][1] == fw:
            j += 1
        if fw and fw not in ignore and j - k + 1 >= run_n:
            rep.by("parallelRun", "style.parallel-run", f"scenes {all_sents[k][0]}..{all_sents[j][0]}",
                   f"{j - k + 1} sentences in a row start with \"{fw}\"")
        k = j + 1
    counts = {}
    for sid, fw, s in all_sents:
        if fw and fw not in ignore:
            counts.setdefault(fw, []).append(sid)
    for fw, sids in sorted(counts.items()):
        if len(sids) >= tv("sameOpenerMax"):
            rep.by("sameOpenerMax", "style.same-opener", "script",
                   f"{len(sids)} sentences start with \"{fw}\" (scenes {', '.join(sids)})")
    return all_sents


def lint_density(scenes, rep, project):
    tl_path = os.path.join(project, "timeline.json")
    voice = {}
    if os.path.isfile(tl_path):
        try:
            with open(tl_path) as fh:
                voice = {s["id"]: s.get("voiceDur") or s.get("length") for s in json.load(fh).get("scenes", [])}
        except (ValueError, KeyError, AttributeError):
            rep.warn("density.bad-timeline", "", "timeline.json", "unreadable; estimating durations from words")
    secs, sents, estimated = 0.0, 0, False
    for sc in scenes:
        if not sc.get("facts"):
            continue
        sents += len(sentences(sc["text"]))
        if sc["id"] in voice and voice[sc["id"]]:
            secs += voice[sc["id"]]
        else:
            secs += word_count(sc["text"]) / tv("wordsPerSecond")
            estimated = True
    if not sents:
        return None
    ratio = secs / sents
    src = "estimated from word count" if estimated else "timeline.json voiceDur"
    if ratio > tv("factDensity"):
        rep.by("factDensity", "density.sparse", "script",
               f"{ratio:.2f} s per fact-bearing sentence ({src}); target <= {tv('factDensity')}")
    return ratio, src

# ---------------------------------------------------------------- credits

def credit_line(s):
    if s.get("attribution"):
        return s["attribution"].strip()
    bits = [s.get("title", "").strip(), s.get("publisher", "").strip()]
    line = ", ".join(b for b in bits if b) + "."
    if s.get("url"):
        line += " " + s["url"]
    if s.get("licence"):
        line += f" Licence: {s['licence']}."
    if s.get("modified"):
        line += f" Modified: {s['modified']}."
    return line


def write_credits(out_dir, scenes, fx, src, rep):
    os.makedirs(out_dir, exist_ok=True)
    cited = []
    for sc in scenes:
        for fid in sc.get("facts", []):
            for sid in fx.get(fid, {}).get("sources", []) or []:
                if sid in src and sid not in cited:
                    cited.append(sid)
    assets = [sid for sid, s in src.items() if s.get("kind") in tv("assetKinds") and sid not in cited]
    keep = [sid for sid in cited + assets if src[sid].get("role") != "rejected"]
    lines = [credit_line(src[sid]) for sid in keep]
    with open(os.path.join(out_dir, "pinned-comment.txt"), "w") as fh:
        fh.write("Sources and credits\n" + "\n".join(lines) + "\n")
    # caption draft
    hook = sentences(scenes[0]["text"])[0] if scenes else ""
    if len(hook) > tv("hookMaxChars"):
        cut = hook[:tv("hookMaxChars")].rsplit(" ", 1)[0]
        rep.warn("credits.hook-too-long", "hookMaxChars", "caption-draft.txt",
                 f"scene 1's first sentence is {len(hook)} chars; trimmed, rewrite it by hand")
        hook = cut
    used = [fx[fid] for sc in scenes for fid in sc.get("facts", []) if fid in fx]
    seen, pre = set(), []
    for f in used:
        if f["id"] in seen:
            continue
        seen.add(f["id"])
        if f.get("status") == "contested" and f.get("caveat"):
            pre.append(f"Note: {f['caveat']}")
        if f.get("mustPreempt"):
            pre.append(f"Note: {f['mustPreempt']}")
        if f.get("status") == "illustrative":
            pre.append(f"Illustrative: {f.get('claim', '')}")
    body = [hook,
            "TODO why: one line on the mechanism.",
            "TODO evidence: one line with a date and a number."]
    body += pre
    body += ["", "Sources:"]
    body += [f"- {src[sid].get('title', '')}, {src[sid].get('publisher', '')}. {src[sid].get('url', '')}".rstrip()
             for sid in cited if src[sid].get("kind") not in tv("assetKinds") and src[sid].get("role") != "rejected"]
    body += ["", tv("aiVoiceDisclosure"), "", "#TODO_channel #TODO_topic"]
    with open(os.path.join(out_dir, "caption-draft.txt"), "w") as fh:
        fh.write("\n".join(body) + "\n")
    return keep

# ---------------------------------------------------------------- run

def run(project, strict=False, credits=None, out=sys.stdout, quiet=False):
    rep = Report()
    mode, scenes = load_script(os.path.join(project, "SCRIPT.json"), rep)
    facts = load_json(os.path.join(project, "facts", "FACTS.json"), rep, "ledger.unreadable", "facts/FACTS.json")
    sources = load_json(os.path.join(project, "facts", "SOURCES.json"), rep, "ledger.unreadable", "facts/SOURCES.json")
    fx, src = validate_ledger(facts if facts is not None else [], sources if sources is not None else [], rep, project)
    density = None
    if scenes:
        lint_links(scenes, fx, src, rep, mode)
        lint_numbers(scenes, fx, src, rep, project)
        lint_style(scenes, rep)
        density = lint_density(scenes, rep, project)
        if credits:
            write_credits(credits, scenes, fx, src, rep)
    if strict:
        rep.strictify()
    if not quiet:
        rep.print(out)
        by = {}
        for f in fx.values():
            by[f.get("status")] = by.get(f.get("status"), 0) + 1
        print(f"\nledger: {len(fx)} facts {dict(sorted((str(k), v) for k, v in by.items()))}, {len(src)} sources;"
              f" script: {len(scenes)} scenes, mode {mode or 'cs'}", file=out)
        if density:
            print(f"fact density: {density[0]:.2f} s per fact-bearing sentence ({density[1]})", file=out)
        if credits:
            print(f"credits: wrote {os.path.join(credits, 'pinned-comment.txt')} and caption-draft.txt", file=out)
        print(f"{rep.count('error')} errors, {rep.count('warn')} warnings", file=out)
    return rep

# ---------------------------------------------------------------- self-test

def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + msg)
        ok = ok and cond

    def vals(t):
        return [(round(n.value, 6), n.percent, n.kind) for n in checkable(parse_numbers(t))]

    cases = [
        ("seventy-one percent", [(71, True, "number")]),
        ("one point five billion", [(1.5e9, False, "number")]),
        ("a fifth of them", [(0.2, False, "fraction")]),
        ("twice as fast", [(2, False, "multiplier")]),
        ("three times faster", [(3, False, "multiplier")]),
        ("one hundred percent", [(100, True, "number")]),
        ("A thousand words means a million comparisons", [(1000, False, "number"), (1e6, False, "number")]),
        ("In 1890, and in 2017", [(1890, False, "year"), (2017, False, "year")]),
        ("1.5B parameters and 71.2% and 1,500,000,000", [(1.5e9, False, "number"), (71.2, True, "number"), (1.5e9, False, "number")]),
        ("change one word, the one I need, two models", []),
        ("three hundred and twenty tokens", [(320, False, "number")]),
        ("two thirds of the layers", [(2 / 3, False, "fraction")]),
        ("GPT-4 and H100 and 3D", []),
        ("half the time", [(0.5, False, "fraction")]),
        ("twenty one", [(21, False, "number")]),
    ]
    for text, want in cases:
        got = vals(text)
        check(got == [(round(v, 6), p, k) for v, p, k in want], f"parse {text!r} -> {got}")
    tol = tv("numberTolerance")
    n = lambda t: checkable(parse_numbers(t))[0]
    check(num_match(n("seventy-one percent"), n("71.2%"), tol), "71% backed by 71.2%")
    check(not num_match(n("over 75%"), n("71.2%"), tol), "75% not backed by 71.2%")
    check(num_match(n("a fifth"), n("20%"), tol), "a fifth == 20%")
    check(num_match(n("one hundred percent"), n("sum to 1"), tol), "100% == 1 (fraction)")
    check(num_match(n("one point five billion"), n("1,500,000,000"), tol), "1.5 billion == 1,500,000,000")
    check(not num_match(n("in 1890"), n("in 1891"), tol), "years exact")
    check(word_count("A thousand words means a million comparisons, in every layer.") == 8, "numbers count as one word")
    check(canonical_words("add up to one hundred percent") == canonical_words("add up to 100%"), "WER canonical numbers")

    today = dt.date.today().isoformat()
    old = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    tmp = tempfile.mkdtemp(prefix="check_facts_selftest_")
    try:
        os.makedirs(os.path.join(tmp, "facts"))
        os.makedirs(os.path.join(tmp, "sources"))
        with open(os.path.join(tmp, "sources", "s1.md"), "w") as fh:
            fh.write("The model scores 71.2% on the benchmark with 1.5B parameters.")
        sources = [
            {"id": "s-0001", "title": "Model card", "url": "https://example.org/card", "publisher": "Example Lab",
             "accessed": today, "tier": 1, "kind": "official", "saved": "sources/s1.md"},
            {"id": "s-0002", "title": "Bed track", "url": "https://example.org/music", "publisher": "Freesound",
             "accessed": today, "kind": "music", "licence": "CC BY 4.0",
             "attribution": "\"Bed\" by someone, CC BY 4.0, https://example.org/music"},
        ]
        facts = [
            {"id": "f-0001", "claim": "The model has 1.5B parameters.", "value": "1.5B", "status": "verified",
             "sources": ["s-0001"], "checkedAt": today},
            {"id": "f-0002", "claim": "It scores on the benchmark.", "status": "verified", "sources": ["s-0001"],
             "checkedAt": today, "who_measured": "independent"},
            {"id": "f-0003", "claim": "Example weights of 60% and 40%.", "status": "illustrative", "checkedAt": today},
        ]
        good = [
            {"id": "hook", "text": "Example Lab built a model with one point five billion parameters. Its score was seventy-one percent.",
             "facts": ["f-0001", "f-0002"], "onscreen": ["71.2%"]},
            {"id": "weights", "text": "The example weights are sixty percent and forty percent.", "facts": ["f-0003"],
             "onscreen": ["illustrative"]},
            {"id": "end", "text": "Example Lab made a small model score high."},
        ]
        def write(script, f=facts, s=sources):
            for name, data in (("SCRIPT.json", script), ("facts/FACTS.json", f), ("facts/SOURCES.json", s)):
                with open(os.path.join(tmp, name), "w") as fh:
                    json.dump(data, fh)
        write(good)
        rep = run(tmp, credits=os.path.join(tmp, "out"), quiet=True)
        check(rep.count("error") == 0, f"clean project has no errors (got {sorted(rep.rules('error'))})")
        pc = open(os.path.join(tmp, "out", "pinned-comment.txt")).read()
        cd = open(os.path.join(tmp, "out", "caption-draft.txt")).read()
        check("\"Bed\" by someone" in pc and "Model card" in pc, "pinned comment has verbatim + fallback credits")
        check(cd.startswith("Example Lab built") and "Sources:" in cd and "AI-generated" in cd, "caption draft skeleton")

        bad = [
            {"id": "hook", "text": "It turns out the model has two billion parameters: really, truly huge. It scored 90%.",
             "facts": ["f-0001", "f-0009"]},
            {"id": "weights", "text": "The example weights are sixty percent and forty percent.", "facts": ["f-0003"]},
            {"id": "m2", "text": "Weights go up. Weights go down. Weights go sideways. " + "word " * 30 + "end.",
             "facts": ["f-0004"]},
            {"id": "end", "text": "That was 3:45 of attention."},
        ]
        facts_bad = facts + [
            {"id": "f-0004", "claim": "The model is the best today.", "status": "contested", "sources": ["s-0003"],
             "checkedAt": "2026/01/01"},
            {"id": "f-0004", "claim": "dup", "status": "maybe", "checkedAt": today},
            {"id": "f-0005", "claim": "Fresh claim.", "status": "unverified", "checkedAt": today, "asOf": old,
             "sources": ["s-0099"]},
        ]
        sources_bad = sources + [{"id": "s-0003", "title": "Pic", "publisher": "X", "accessed": today, "kind": "image"}]
        write({"mode": "news", "scenes": bad}, facts_bad, sources_bad)
        rep = run(tmp, quiet=True)
        expect = {"style.banned-mark", "style.banned-phrase", "style.intensifiers", "style.pronoun-opener",
                  "style.parallel-run", "style.long-sentence", "numbers.unbacked", "links.unknown-fact",
                  "links.illustrative-untagged", "links.contested-no-caveat", "ledger.duplicate-id",
                  "ledger.bad-status", "ledger.bad-date", "ledger.missing-source", "ledger.asset-no-licence",
                  "links.news-no-asof"}
        missing = expect - rep.rules()
        check(not missing, f"bad project flags every planted problem (missing: {sorted(missing)})")
        marks = [i for i in rep.items if i[1] == "style.banned-mark"]
        check(len(marks) == 1, f"digit:digit colon ignored, prose colon flagged ({len(marks)} mark findings)")
        unb = {i[4].split('"')[1] for i in rep.items if i[1] == "numbers.unbacked"}
        check({"two billion", "90%"} <= unb,
              f"unbacked numbers found: {sorted(unb)}")
        rep2 = run(tmp, strict=True, quiet=True)
        check(rep2.count("warn") == 0 and rep2.count("error") >= rep.count("error") + rep.count("warn"), "--strict promotes warnings")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("self-test", "OK" if ok else "FAILED")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=".", help="project root containing SCRIPT.json and facts/")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--credits", metavar="OUT_DIR", help="write pinned-comment.txt and caption-draft.txt here")
    ap.add_argument("--self-test", action="store_true", help="run built-in tests on synthetic data")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    rep = run(os.path.abspath(a.project), a.strict, a.credits)
    sys.exit(1 if rep.count("error") else 0)


if __name__ == "__main__":
    main()
