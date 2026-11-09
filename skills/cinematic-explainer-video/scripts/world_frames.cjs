// Render the Three.js world composition alone at chosen times, outside HyperFrames.
// Fast iteration on camera, layout and light without a full snapshot; also surfaces page errors.
//
// Usage (from the project root):
//   node world_frames.cjs compositions/world.html 0.5,6.9,37.6 [outDir] [query]
//   query examples: "?nobloom", "?noreflect" (if the template honours them)
// Env overrides: PUPPETEER_CORE=<path to puppeteer-core>, CHROME=<path to chrome / chrome-headless-shell>
// Writes <outDir>/wf_<t>.jpg (default outDir: tmp/world-frames)
const fs = require("fs"), path = require("path"), http = require("http"), os = require("os");

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

const [file, times, outDir = "tmp/world-frames", query = ""] = process.argv.slice(2);
if (!file || !times) { console.log("usage: node world_frames.cjs <composition.html> <t1,t2,...> [outDir] [query]"); process.exit(1); }
fs.mkdirSync(outDir, { recursive: true });
// serve the project root so "assets/..." paths resolve exactly as in HyperFrames
const debugName = "_debug_" + path.basename(file);
fs.copyFileSync(file, debugName);
const types = { ".html": "text/html", ".js": "text/javascript", ".woff2": "font/woff2", ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const p = path.join(process.cwd(), decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(process.cwd()) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": types[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
}).listen(0, "127.0.0.1", async () => {
  const port = server.address().port;
  const puppeteer = require(findPuppeteer());
  const b = await puppeteer.launch({ executablePath: findChrome(), protocolTimeout: 300000 });
  try {
    const p = await b.newPage(); await p.setViewport({ width: 1080, height: 1920 });
    p.on("pageerror", (e) => console.log("pageerror", e.message));
    p.on("console", (m) => { if (m.type() === "error") console.log("console.error", m.text().slice(0, 300)); });
    await p.goto(`http://127.0.0.1:${port}/${debugName}${query}`, { waitUntil: "load", timeout: 120000 });
    // the world registers window.__hf.buildReady[<id>] and exposes a render(t) host (see SKILL.md)
    await p.evaluate(async () => { await Promise.all(Object.values((window.__hf && window.__hf.buildReady) || {})); });
    for (const t of times.split(",").map(Number)) {
      const data = await p.evaluate((t) => {
        const host = window.__world; host.render(t);
        return document.querySelector("canvas").toDataURL("image/jpeg", 0.85);
      }, t);
      const out = path.join(outDir, `wf_${t}.jpg`);
      fs.writeFileSync(out, Buffer.from(data.split(",")[1], "base64"));
      console.log("wrote", out);
    }
  } finally {
    await b.close(); server.close(); fs.unlinkSync(debugName);
  }
});
