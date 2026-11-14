// Screenshot an announcement page or an arXiv abstract page as evidence for a news video.
//
// Usage:
//   node scripts/news_shot.cjs <url> <out.png> [--mode article|selector|full] [--selector css]
//        [--highlight "key phrase"] [--width 1200] [--height 1500] [--scale 2] [--wait 1500] [--paras 4]
//
//   article  (default) headline + first paragraphs (arXiv: title, authors, abstract)
//   selector one element, e.g. --selector "figure:nth-of-type(2)" or "table"
//   full     the whole page (capped at 16000 CSS px tall)
//
// Before capture it hides cookie/consent/newsletter/chat overlays, modal dialogs, sticky/fixed headers
// and bottom bars, and unlocks scrolling. It never draws on the image.
//
// Writes <out>.json next to the PNG (out.png -> out.json): url, final_url, title, og_image, captured_at
// (UTC), clip, image size and, with --highlight, every match of the phrase as boxes in OUTPUT-IMAGE PIXELS
// (x, y, width, height from the top-left of the PNG), plus the same boxes normalised to 0..1, so a
// HyperFrames scene can draw a highlighter exactly over the real text.
//
// Rules: a fresh temporary browser profile every run (never a logged-in session); x.com / twitter.com are
// refused: use oEmbed (https://publish.twitter.com/oembed?url=<tweet>&omit_script=1) and build our own card.
// Env overrides: PUPPETEER_CORE=<path to puppeteer-core>, CHROME=<path to chrome / chrome-headless-shell>
// Exit: 0 ok · 1 error · 2 usage · 3 refused URL · 4 captured, but the page looks like a bot wall/error page.
const fs = require("fs"), path = require("path"), os = require("os");

// --- resolver: same logic as scripts/world_frames.cjs (copied so this script is standalone) ---
function findPuppeteer() {
  if (process.env.PUPPETEER_CORE) return process.env.PUPPETEER_CORE;
  try { return require.resolve("puppeteer-core"); } catch (e) {}
  const npx = path.join(os.homedir(), ".npm", "_npx");
  for (const d of fs.existsSync(npx) ? fs.readdirSync(npx) : []) {
    const p = path.join(npx, d, "node_modules", "puppeteer-core");
    if (fs.existsSync(p)) return p;
  }
  throw new Error("puppeteer-core not found: run any `npx hyperframes` command once, or set PUPPETEER_CORE");
}
function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const base = path.join(os.homedir(), ".cache", "hyperframes", "chrome");
  const stack = [base];
  while (stack.length) {
    const d = stack.pop();
    if (!fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d)) {
      const p = path.join(d, f);
      if (f === "chrome-headless-shell" && fs.statSync(p).isFile()) return p;
      if (fs.statSync(p).isDirectory()) stack.push(p);
    }
  }
  throw new Error("chrome-headless-shell not found under ~/.cache/hyperframes/chrome: set CHROME");
}

// --- args ---
const USAGE = 'usage: node news_shot.cjs <url> <out.png> [--mode article|selector|full] [--selector css] [--highlight "phrase"] [--width 1200] [--height 1500] [--scale 2] [--wait 1500] [--paras 4]';
function parseArgs(argv) {
  const o = { mode: "article", width: 1200, height: 1500, scale: 2, wait: 1500, paras: 4, pos: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") { console.log(USAGE); process.exit(0); }
    if (a.startsWith("--")) {
      const k = a.slice(2), v = argv[++i];
      if (v === undefined) fail(2, `missing value for ${a}\n${USAGE}`);
      if (["width", "height", "scale", "wait", "paras"].includes(k)) {
        const n = Number(v);
        if (!Number.isFinite(n) || n <= 0) fail(2, `--${k} must be a positive number`);
        o[k] = n;
      } else if (["mode", "selector", "highlight"].includes(k)) o[k] = v;
      else fail(2, `unknown option ${a}\n${USAGE}`);
    } else o.pos.push(a);
  }
  if (o.pos.length !== 2) fail(2, USAGE);
  if (!["article", "selector", "full"].includes(o.mode)) fail(2, "--mode must be article, selector or full");
  if (o.mode === "selector" && !o.selector) fail(2, "--mode selector needs --selector <css>");
  if (o.selector && o.mode === "article") o.mode = "selector";
  return o;
}
function fail(code, msg) { console.error(msg); process.exit(code); }

const X_HOSTS = /(^|\.)(x\.com|twitter\.com)$/i;
function checkUrl(u) {
  let url;
  try { url = new URL(u); } catch (e) { fail(2, `not a URL: ${u}`); }
  if (!/^https?:$/.test(url.protocol)) fail(3, `refused: only http(s) URLs (${url.protocol})`);
  if (X_HOSTS.test(url.hostname)) {
    fail(3, `refused: no screenshots of x.com / twitter.com (logged-in UI, account risk). Resolve the post with oEmbed and build our own quote card:\n  https://publish.twitter.com/oembed?url=${encodeURIComponent(u)}&omit_script=1`);
  }
  return url;
}

// --- in-page helpers (serialised into the page) ---
function hideOverlays() {
  const RX = /cookie|consent|gdpr|ccpa|onetrust|didomi|truste|usercentrics|cookiebot|osano|termly|quantcast|cmp-|privacy-?banner|newsletter|subscribe|signup|sign-up|paywall|regwall|modal|popup|pop-up|overlay|lightbox|interstitial|banner|toast|snackbar|intercom|drift|hubspot|chat-?widget|app-?banner|smartbanner|announcement-?bar|promo|notification-?bar|login-?prompt/i;
  const STRICT = /cookie|consent|gdpr|onetrust|cookiebot|didomi|usercentrics|truste/i;
  const KNOWN = '#onetrust-consent-sdk,#onetrust-banner-sdk,#CybotCookiebotDialog,#usercentrics-root,#didomi-host,.fc-consent-root,#qc-cmp2-container,[id^="sp_message_container"],.truste_overlay,.truste_box_overlay,#credential_picker_container,#intercom-container,.intercom-lightweight-app,.grecaptcha-badge,iframe[src*="consent"],iframe[title*="consent" i],iframe[title*="cookie" i]';
  const hide = (el) => { if (el.dataset.nsHidden) return 0; el.style.setProperty("display", "none", "important"); el.dataset.nsHidden = "1"; return 1; };
  let n = 0;
  document.querySelectorAll(KNOWN).forEach((el) => { n += hide(el); });
  const sigOf = (el) => `${el.id || ""} ${typeof el.className === "string" ? el.className : el.getAttribute("class") || ""} ${el.getAttribute("role") || ""} ${el.getAttribute("aria-label") || ""}`;
  for (const el of document.querySelectorAll("body *")) {
    if (el.dataset.nsHidden) continue;
    const cs = getComputedStyle(el);
    const content = el.querySelector("h1, article, main");
    const sig = sigOf(el);
    // consent banners are sometimes in normal flow: hide those regardless of position if they are small
    if (STRICT.test(sig) && !content && (el.innerText || "").length < 3000 && el.tagName !== "BODY") { n += hide(el); continue; }
    if (cs.position !== "fixed" && cs.position !== "sticky") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const dialog = el.getAttribute("role") === "dialog" || el.getAttribute("aria-modal") === "true";
    const big = r.height > innerHeight * 0.5 && r.width > innerWidth * 0.5 && !content;  // a page-covering layer
    const header = r.top <= 10 && r.height < 260;                                       // fixed/sticky nav bars
    const bottom = r.bottom >= innerHeight - 4 && r.height < innerHeight * 0.5;           // cookie/app bars at the bottom
    if (RX.test(sig) || dialog || big || header || bottom) n += hide(el);
  }
  for (const el of [document.documentElement, document.body]) {
    if (!el) continue;
    el.style.setProperty("overflow", "visible", "important");
    el.style.setProperty("overflow-y", "visible", "important");
    el.classList.remove("modal-open", "no-scroll", "noscroll", "overflow-hidden", "is-locked");
  }
  document.documentElement.style.scrollBehavior = "auto";
  return n;
}

function articleRect(maxParas, maxHeight) {
  // arXiv abstract page: dateline + title + authors + abstract, left column only
  if (/(^|\.)arxiv\.org$/.test(location.hostname) && /^\/abs\//.test(location.pathname)) {
    const parts = [".dateline", "h1.title", ".authors", "blockquote.abstract"].map((q) => document.querySelector(q)).filter(Boolean);
    if (parts.length >= 2 && document.querySelector("blockquote.abstract")) {
      const rs = parts.map((el) => el.getBoundingClientRect());
      const pad = 12;
      const x = Math.max(0, Math.min(...rs.map((r) => r.left)) + scrollX - pad), y = Math.max(0, Math.min(...rs.map((r) => r.top)) + scrollY - pad);
      const right = Math.max(...rs.map((r) => r.right)) + scrollX + pad, bottom = Math.max(...rs.map((r) => r.bottom)) + scrollY + pad;
      return { x, y, width: right - x, height: Math.min(maxHeight * 2, bottom - y), headline: (document.querySelector("h1.title") || {}).innerText || "" };
    }
  }
  const vis = (el) => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 100 && r.height > 8 && cs.visibility !== "hidden" && cs.display !== "none" && Number(cs.opacity) > 0.05; };
  const fsz = (el) => parseFloat(getComputedStyle(el).fontSize) || 0;
  const docTop = (el) => el.getBoundingClientRect().top + scrollY;
  const len = (el) => (el.innerText || "").replace(/\s+/g, "").length;
  let heads = [...document.querySelectorAll("h1")].filter((h) => vis(h) && len(h) >= 4 && len(h) <= 320 && docTop(h) < 2600);
  if (!heads.length) heads = [...document.querySelectorAll('h2, [class*="title" i]')].filter((h) => vis(h) && len(h) >= 6 && len(h) <= 220 && fsz(h) >= 20 && docTop(h) < 2000);
  if (!heads.length) return null;
  const head = heads.sort((a, b) => fsz(b) - fsz(a) || docTop(a) - docTop(b))[0];
  const range = document.createRange(); range.selectNodeContents(head);
  const tr = range.getBoundingClientRect();
  const hrv = tr.width > 50 ? tr : head.getBoundingClientRect();
  const H = { left: hrv.left + scrollX, right: hrv.right + scrollX, top: hrv.top + scrollY, bottom: hrv.bottom + scrollY };
  const mid = (H.left + H.right) / 2;
  const leaf = (el) => /^(P|BLOCKQUOTE)$/.test(el.tagName) || (!el.querySelector("p, div, section, article, ul, ol, table, blockquote") && len(el) >= 60);
  const blocks = [...document.querySelectorAll('p, blockquote, div, span[class*="text" i]')]
    .filter((el) => vis(el) && !el.contains(head) && !head.contains(el) && len(el) >= 20 && leaf(el))
    .map((el) => { const r = el.getBoundingClientRect(); return { el, left: r.left + scrollX, right: r.right + scrollX, top: r.top + scrollY, bottom: r.bottom + scrollY, width: r.width }; })
    .filter((b) => b.top >= H.bottom - 4 && b.width <= 1100 && ((b.left <= mid && b.right >= mid) || Math.min(b.right, H.right) - Math.max(b.left, H.left) >= b.width * 0.5))
    .sort((a, b) => a.top - b.top);
  const pad = 32;
  let left = H.left, right = H.right, bottom = H.bottom, lastBottom = H.bottom, taken = 0, used = 0;
  for (const b of blocks) {
    if (++used > maxParas * 3) break;                    // short blocks count too, so page furniture ends the clip
    if (b.top - lastBottom > 1100) break;                // a big gap (beyond a hero image): the article column ended
    if (b.bottom - H.top + pad * 2 > maxHeight && taken) break;
    left = Math.min(left, b.left); right = Math.max(right, b.right); bottom = Math.max(bottom, b.bottom); lastBottom = b.bottom;
    if (b.el.tagName === "P" || b.el.tagName === "BLOCKQUOTE" || len(b.el) >= 120) taken++;
    if (taken >= maxParas) break;
  }
  const docW = Math.max(document.documentElement.scrollWidth, innerWidth);
  if (right - left < 640) { const m = (left + right) / 2; left = m - 320; right = m + 320; }
  const x = Math.max(0, left - pad), y = Math.max(0, H.top - pad - 8);
  const width = Math.min(docW - x, right - left + pad * 2);
  const height = Math.min(maxHeight, bottom - y + pad);
  return { x, y, width, height, headline: (head.innerText || "").trim().slice(0, 300) };
}

function findPhrase(phrase) {
  const normCh = (c) => {
    if (/\s/.test(c)) return " ";
    if (/[‘’‛′]/.test(c)) return "'";
    if (/[“”‟″]/.test(c)) return '"';
    if (/[‐-―−]/.test(c)) return "-";
    return c.toLowerCase()[0];
  };
  const target = [...phrase].map(normCh).join("").replace(/ +/g, " ").trim();
  if (!target) return [];
  const isInline = (el) => el && getComputedStyle(el).display.startsWith("inline");
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      const p = n.parentElement;
      if (!p || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(p.tagName)) return NodeFilter.FILTER_REJECT;
      if (!p.offsetParent && getComputedStyle(p).position !== "fixed") return NodeFilter.FILTER_REJECT;  // display:none
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  let buf = ""; const mapN = [], mapO = []; let prevParent = null;
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const p = n.parentElement;
    if (prevParent && p !== prevParent && (!isInline(p) || !isInline(prevParent)) && buf && buf[buf.length - 1] !== " ") { buf += " "; mapN.push(null); mapO.push(0); }
    const t = n.nodeValue;
    for (let i = 0; i < t.length; i++) {
      const c = normCh(t[i]);
      if (c === " " && (buf.length === 0 || buf[buf.length - 1] === " ")) continue;
      buf += c; mapN.push(n); mapO.push(i);
    }
    prevParent = p;
  }
  const out = [];
  for (let at = buf.indexOf(target); at !== -1 && out.length < 20; at = buf.indexOf(target, at + 1)) {
    let s = at, e = at + target.length - 1;
    while (s <= e && !mapN[s]) s++;
    while (e >= s && !mapN[e]) e--;
    if (s > e) continue;
    const r = document.createRange();
    r.setStart(mapN[s], mapO[s]); r.setEnd(mapN[e], mapO[e] + 1);
    const rects = [...r.getClientRects()].filter((q) => q.width > 1 && q.height > 1)
      .map((q) => ({ x: q.left + scrollX, y: q.top + scrollY, width: q.width, height: q.height }))
      .sort((a, b) => a.y - b.y || a.x - b.x);
    const merged = [];
    for (const q of rects) {   // one box per line
      const m = merged.find((k) => Math.abs(k.y - q.y) < 3 && Math.abs(k.height - q.height) < 6 && q.x <= k.x + k.width + 4 && q.x + q.width >= k.x - 4);
      if (m) { const x1 = Math.min(m.x, q.x), x2 = Math.max(m.x + m.width, q.x + q.width); m.x = x1; m.width = x2 - x1; m.height = Math.max(m.height, q.height); }
      else merged.push({ ...q });
    }
    if (merged.length && isShown(mapN[s].parentElement, merged[0])) out.push({ text: r.toString().replace(/\s+/g, " ").trim(), rects: merged });
  }
  window.scrollTo(0, 0);
  return out;

  // Text that is collapsed, transparent, clipped or covered must not get a highlight box:
  // check the ancestors' styles, then hit-test the middle of the first line.
  function isShown(el, q) {
    for (let a = el; a; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) < 0.05) return false;
    }
    window.scrollTo(0, Math.max(0, q.y - innerHeight / 2));
    const hit = document.elementFromPoint(q.x - scrollX + Math.min(q.width / 2, 20), q.y - scrollY + q.height / 2);
    return !!hit && (hit === el || el.contains(hit) || (hit.contains(el) && hit.tagName !== "BODY" && hit.tagName !== "HTML" && getComputedStyle(el).display.startsWith("inline")));
  }
}

function pageMeta() {
  const meta = (sel) => { const m = document.querySelector(sel); return m ? m.getAttribute("content") : null; };
  const abs = (u) => { try { return u ? new URL(u, location.href).href : null; } catch (e) { return null; } };
  const canonical = document.querySelector('link[rel="canonical"]');
  return {
    title: (document.title || "").trim(), og_title: meta('meta[property="og:title"]'), og_image: abs(meta('meta[property="og:image"]') || meta('meta[name="twitter:image"]')),
    published_time: meta('meta[property="article:published_time"]') || meta('meta[name="citation_date"]') || meta('meta[name="citation_online_date"]'),
    canonical: canonical ? abs(canonical.getAttribute("href")) : null, site_name: meta('meta[property="og:site_name"]'),
    body_text_head: ((document.body && document.body.innerText) || "").replace(/\s+/g, " ").trim().slice(0, 300),
    body_text_len: ((document.body && document.body.innerText) || "").replace(/\s+/g, "").length,
    doc_width: Math.max(document.documentElement.scrollWidth, innerWidth), doc_height: Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0),
  };
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  if (b.length < 24 || b.toString("ascii", 12, 16) !== "IHDR") return null;
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BOT_WALL = /just a moment|attention required|access denied|verify you are human|are you a robot|captcha|403 forbidden|404 not found|page not found|error 40\d/i;

async function main() {
  const o = parseArgs(process.argv.slice(2));
  const [urlIn, outPng] = o.pos;
  checkUrl(urlIn);
  if (!/\.png$/i.test(outPng)) fail(2, "out file must end in .png");
  const sidecar = outPng.replace(/\.png$/i, ".json");
  fs.mkdirSync(path.dirname(path.resolve(outPng)), { recursive: true });
  const warnings = [];
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "news-shot-"));  // fresh, empty profile: never logged in
  const puppeteer = require(findPuppeteer());
  const browser = await puppeteer.launch({
    executablePath: findChrome(), userDataDir: profile, protocolTimeout: 120000,
    args: ["--no-first-run", "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars", "--mute-audio", "--disable-notifications", "--lang=en-US"],
  });
  let code = 0;
  try {
    const page = await browser.newPage();
    const ua = (await browser.userAgent()).replace(/HeadlessChrome/g, "Chrome");
    try { await page.setUserAgent({ userAgent: ua }); } catch (e) { await page.setUserAgent(ua); }
    await page.setExtraHTTPHeaders({ "Accept-Language": "en-US,en;q=0.9" });
    await page.setViewport({ width: Math.round(o.width), height: Math.round(o.height), deviceScaleFactor: o.scale });
    let failedSameOrigin = 0;
    const origin = new URL(urlIn).hostname.replace(/^www\./, "");
    page.on("response", (r) => {
      try { if (r.status() >= 400 && new URL(r.url()).hostname.endsWith(origin) && ["document", "script", "fetch", "xhr"].includes(r.request().resourceType())) failedSameOrigin++; } catch (e) {}
    });
    let resp = null;
    try {
      resp = await page.goto(urlIn, { waitUntil: "networkidle2", timeout: 45000 });
    } catch (e) {
      if (!/timeout/i.test(e.message)) throw e;
      warnings.push("navigation did not go idle in 45 s; captured what had loaded");
    }
    const finalUrl = page.url();
    if (X_HOSTS.test(new URL(finalUrl).hostname)) fail(3, `refused: ${urlIn} redirected to ${finalUrl} (x.com/twitter.com). Use oEmbed: https://publish.twitter.com/oembed?url=${encodeURIComponent(finalUrl)}&omit_script=1`);
    const status = resp ? resp.status() : null;
    await sleep(o.wait);
    try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch (e) {}
    let hidden = await page.evaluate(hideOverlays);
    // scroll through the top of the page so lazy images and sticky-on-scroll bars appear, then hide again
    await page.evaluate(async (h) => { for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)); } window.scrollTo(0, 0); }, o.mode === "full" ? 16000 : 3000);
    await sleep(400);
    hidden += await page.evaluate(hideOverlays);
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(300);
    const meta = await page.evaluate(pageMeta);
    let clip = null, headline = null;
    if (o.mode === "article") {
      const r = await page.evaluate(articleRect, o.paras, o.height);
      if (r) { headline = r.headline; clip = { x: r.x, y: r.y, width: r.width, height: r.height }; }
      else { warnings.push("no headline found: captured the top of the page"); clip = { x: 0, y: 0, width: o.width, height: o.height }; }
    } else if (o.mode === "selector") {
      const r = await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const q = el.getBoundingClientRect();
        return { x: q.left + scrollX, y: q.top + scrollY, width: q.width, height: q.height };
      }, o.selector);
      if (!r || r.width < 2 || r.height < 2) fail(1, `selector not found or not visible: ${o.selector}`);
      const pad = 12;
      clip = { x: Math.max(0, r.x - pad), y: Math.max(0, r.y - pad), width: r.width + pad * 2, height: r.height + pad * 2 };
    } else {
      const h = Math.min(meta.doc_height, 16000);
      if (meta.doc_height > 16000) warnings.push(`page is ${meta.doc_height} px tall: full capture capped at 16000`);
      clip = { x: 0, y: 0, width: meta.doc_width, height: h };
    }
    let matches = null;
    if (o.highlight) {
      matches = await page.evaluate(findPhrase, o.highlight);
      // article mode: if the phrase sits just below the clip (e.g. later in an abstract), extend the clip to it
      if (o.mode === "article" && matches.length) {
        const inside = matches.some((m) => m.rects.every((q) => q.y >= clip.y && q.y + q.height <= clip.y + clip.height));
        const first = matches[0].rects[matches[0].rects.length - 1];
        if (!inside && first.y > clip.y && first.y + first.height - clip.y + 40 <= o.height * 2) {
          clip.height = first.y + first.height - clip.y + 40;
          warnings.push("clip extended down to include the highlight");
        }
      }
    }
    // clip in document coordinates (page scrolled to 0,0); integer CSS px keep the pixel mapping exact
    clip = { x: Math.floor(clip.x), y: Math.floor(clip.y), width: Math.ceil(clip.width), height: Math.ceil(clip.height) };
    clip.width = Math.min(clip.width, meta.doc_width - clip.x);
    await page.screenshot({ path: outPng, clip, captureBeyondViewport: true });
    const img = pngSize(outPng) || { width: Math.round(clip.width * o.scale), height: Math.round(clip.height * o.scale) };
    const sx = img.width / clip.width, sy = img.height / clip.height;
    const r1 = (v) => Math.round(v * 10) / 10, r4 = (v) => Math.round(v * 10000) / 10000;
    let highlight = null;
    if (o.highlight) {
      const ms = matches.map((m) => {
        const boxes = m.rects
          .map((q) => {
            const x1 = Math.max(q.x, clip.x), y1 = Math.max(q.y, clip.y);
            const x2 = Math.min(q.x + q.width, clip.x + clip.width), y2 = Math.min(q.y + q.height, clip.y + clip.height);
            if (x2 <= x1 || y2 <= y1) return null;
            return { x: r1((x1 - clip.x) * sx), y: r1((y1 - clip.y) * sy), width: r1((x2 - x1) * sx), height: r1((y2 - y1) * sy) };
          })
          .filter(Boolean);
        return { text: m.text, in_capture: boxes.length === m.rects.length && boxes.length > 0, partially_in_capture: boxes.length > 0 && boxes.length < m.rects.length,
          boxes, boxes_norm: boxes.map((b) => ({ x: r4(b.x / img.width), y: r4(b.y / img.height), width: r4(b.width / img.width), height: r4(b.height / img.height) })) };
      });
      const inCap = ms.filter((m) => m.boxes.length);
      highlight = { phrase: o.highlight, found: matches.length > 0, matches_total: matches.length, matches_in_capture: inCap.length, matches: inCap };
      if (!matches.length) warnings.push(`highlight phrase not found in the page text: "${o.highlight}"`);
      else if (!inCap.length) warnings.push("highlight phrase found, but outside the captured area (try --mode full or a larger --height)");
    }
    // bot walls often answer 200 and then render an error client-side (openai.com: scripts 403 -> "500")
    const errorText = meta.body_text_len < 600 && /\b(403|404|500|502|503)\b|internal server error|access denied|forbidden|just a moment|verify you are human|enable javascript/i.test(meta.body_text_head);
    const looksBlocked = BOT_WALL.test(meta.title) || (status && status >= 400) || errorText || failedSameOrigin >= 3;
    if (looksBlocked) {
      warnings.push(`page looks like an error/bot wall (HTTP ${status}, ${failedSameOrigin} failed same-site requests, text "${meta.body_text_head.slice(0, 80)}"): do not use this capture; use the feed's og:image or another primary page`);
      code = 4;
    }
    const out = {
      url: urlIn, final_url: finalUrl, http_status: status, title: meta.og_title || meta.title, document_title: meta.title, headline, site_name: meta.site_name,
      blocked: looksBlocked, og_image: meta.og_image, published_time: meta.published_time, canonical: meta.canonical, captured_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      mode: o.mode, selector: o.selector || null, viewport: { width: o.width, height: o.height, device_scale_factor: o.scale },
      image: { file: path.basename(outPng), width: img.width, height: img.height },
      clip_css_px: clip, px_per_css_px: { x: r4(sx), y: r4(sy) }, overlays_hidden: hidden, highlight,
      coordinates: "boxes are in output-image pixels from the top-left of the PNG; boxes_norm are the same as fractions of the image size",
      warnings,
    };
    fs.writeFileSync(sidecar, JSON.stringify(out, null, 2) + "\n");
    console.log(`wrote ${outPng} (${img.width}x${img.height}) and ${sidecar}${highlight ? ` · highlight: ${highlight.matches_in_capture}/${highlight.matches_total} match(es) in capture` : ""}`);
    for (const w of warnings) console.error("warning: " + w);
  } finally {
    await browser.close();
    fs.rmSync(profile, { recursive: true, force: true });
  }
  process.exit(code);
}

main().catch((e) => { console.error("error: " + (e && e.message ? e.message : e)); process.exit(1); });
