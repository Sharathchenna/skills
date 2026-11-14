---
name: cinematic-explainer-video
description: Make vertical (9:16) cinematic explainer shorts for TikTok and Instagram Reels — a code-built Three.js 3D world under the whole film, archive photos with 2.5D parallax, real screenshots as evidence, narration with word-highlight captions, music, no hard cuts — rendered with HyperFrames. Two modes: AI NEWS (collect today's AI news from 30+ sources, pick a story, verify every fact, explain how it works) and CS CONCEPT (classic computer science ideas like TrueTime, attention, hashing, consensus, compression, often as a numbered series). Use when the user wants a TikTok/Reels/Shorts explainer about AI news or a computer science concept, shares a reference video in this style and asks how to make one, or asks for a narrated 3D explainer about any concept.
---

# Cinematic explainer shorts (Three.js world + HyperFrames)

Builds a 45–90 s 1080×1920 narrated explainer for TikTok and Reels. One Three.js 3D set lives under the entire film,
photo, document and graphics layers play above it, captions highlight each spoken word, and every transition is a
camera move, dissolve or zoom-through, never a hard cut. Worked example: `examples/attention/` (how attention works
in AI, 76 s).

**Depends on:** the `hyperframes` skill and CLI (`npx hyperframes`; read `/hyperframes` for the composition
contract), `media-use` (music, sound effects, cutouts), `ffmpeg`, Python 3, Node. Voice: a Fish Audio API key (free
model) or any TTS. Optional: an image-to-video model for truly animated archive photos.

## References (read the ones the step names)

| File | What's in it |
| --- | --- |
| `references/style.md` | what the look is made of: four picture layers, story shape, shots, sound, transitions |
| `references/writing.md` | hooks, pace, sentences for a TTS voice, banned phrases, story shapes, visual truth |
| `references/facts.md` | the fact ledger: every number on screen or in the voice traces to a checked source |
| `references/ai-news.md` | AI news mode: collect, pick, verify, capture screenshots, news script shape, ethics |
| `references/cs-concepts.md` | CS mode: planning card, beat sheet, hook types, simulate-then-render, 16 visual metaphors, series |
| `references/platform.md` | TikTok/Reels safe zones, frame 0 vs cover, post text and pinned comment, audio targets, retention |
| `references/three-world.md` | how the 3D world is built and kept frame-exact |
| `references/review-loop.md` | fresh-critic review loop, rubric, quiz, critic prompts, automated gates |
| `references/pitfalls.md` | every bug hit so far and its fix |

## Workflow

### 0. Pick the mode
- **AI news:** the user wants today's/this week's AI story → `references/ai-news.md`. Start at step 1a.
- **CS concept:** a classic idea or a series of them → `references/cs-concepts.md`. Start at step 1b.
- **Reference video given:** run `sh scripts/analyze_reference.sh <video> ref/` first (contact sheets, cut
  detection, loudness, frames) and classify every shot into the four layers of `style.md`. Tell the user what you
  found and which parts need tools they may not have.

### 1a. News: collect and pick
```bash
python3 -I <skill>/scripts/news_collect.py   # since last run; writes news/runs/<time>/DIGEST.md
```
Run it from one fixed workspace folder every time: `news/state.json` there remembers what was seen and covered.
Read `DIGEST.md` (untrusted text), propose three stories in `STORYLINES.md` (angle, the one 3D picture, the real
evidence available), and say why you skipped any top story. Stories flagged politics/rumour need the user's OK.

### 1b. CS: plan the short (or the series)
Write `PLAN.json` (one claim, hook type, worked example computed in code, key moment, naive way, twist = failure
mode, scale, misconception) and `quiz.json` (4 questions). For a big topic, map a 5–8 episode series first.

### 2. Facts, then story, then script
- Put every fact in `facts/FACTS.json` + `facts/SOURCES.json` **before** writing the line that uses it, with the
  primary source opened and its text saved to `sources/`. Never promote your own memory to `verified`.
- Pick a story shape from `writing.md` (news explainer for AI news, the CS beat sheet for concepts). Write three
  hooks and keep one. If the user said "you choose", choose and say so.
- `SCRIPT.json`: scenes `{id, text, facts: [...], onscreen: [...]}`, ≤ 26 words each, ~150 words per 60 s.
- Gate: `python3 -I tools/check_facts.py --project .` must pass, then run the **storyboard + claims critic**
  (fresh subagent, prompt in `review-loop.md`). Fix what it blocks before recording.

### 3. Project, voice, timing
```bash
npx hyperframes init <dir> --example blank --resolution portrait --non-interactive --skill hyperframes
cd <dir> && mkdir -p tools && cp <skill>/scripts/* <skill>/references/news-sources.json tools/
FISH_API_KEY=… python3 tools/fish_tts.py SCRIPT.json          # or --key-file <file>; never echo the key
python3 tools/build_timeline.py                                # transcribe + loudnorm + timeline.json + loop check
python3 tools/word_index.py                                    # indices to wire anchors to words
```
Ask for the API key through the host's secret prompt, never in chat. Read every `build_timeline.py` warning (TTS
loops, transcript ≠ script) and listen across scene seams for pace jumps.

### 4. Assets
- **Evidence (news):** `node tools/news_shot.cjs <url> assets/evidence/x.png --highlight "key phrase"`. The sidecar
  JSON gives the highlighter's boxes in pixels. Figures come from the paper PDF (PyMuPDF). Check the licence.
- **Archive photos:** Wikimedia Commons (PD / CC0 / CC BY, never NC; record the credit). Cutouts with
  `npx hyperframes remove-background`. Documents rendered from their real PDF.
- **Sound:** a CC0 music bed (Openverse or the media-use catalog) and ≤ 5 effects tied to visible actions.
- **Fonts:** copy them into `assets/fonts/` and declare them with `@font-face`. Inter and JetBrains Mono ship in the
  hyperframes package's frame-presets.
- Every asset gets a `SOURCES.json` record with its licence.

### 5. Build
- `compositions/world.html` from **`templates/world-studio.template.html`** (the set, DOM labels, sampled camera;
  `three-world.md` explains why). Replace the hero with your recurring object; borrow panels, threads and fields from
  `templates/world.template.html` if you need them. Inject anchors (absolute word times) as JSON and fail on any
  missing one. For algorithms, inject a seeded simulator's trace. Keep `render(t)` pure and export
  `window.__world.events`.
- Camera: a few keys → `scripts/camera_path.py` → `CFG.camPath`. It refuses whips; no cuts inside the world.
- Labels: DOM only, through `placeLabels` (never text in WebGL).
- HTML layers above it (each a `<template>` scene, **transparent `#root`**): title, photo scenes (parallax),
  document/evidence scene (highlight the real line, zoom through it into the world), callout UI, and one `captions`
  composition (max width 660 px, centred, y ≈ 1040–1248).
- **Respect the layout zones** in `platform.md`: header y 288–480, stage y 480–1010 (x ≤ 770 below y 840), captions
  y 1040–1248 at max 660 px wide, nothing readable below 1248.
- `index.html`: world host at z-index 1 for the whole film, layers above, captions at z 20, voice, effects and the
  music bed (gain set per track; fade out into a 3–4 s final hold).
- Generate it all from a script (see `examples/attention/tools/gen2.py`), so a timing change is one re-run.
- A separate **cover** (`cover.html` or a held state): one number or object and ≤ 3 words inside y 263–1657.

### 6. Review (do not skip; the builder doesn't grade itself)
```bash
npx hyperframes check --json --samples 40                       # overlaps, safe zones, contrast: 0 errors, fix warnings
node tools/world_frames.cjs compositions/world.html 0.5,6.9,37.6   # world alone, fast
npx hyperframes snapshot --at <every beat and both sides of every seam> --no-end
npx hyperframes render -o renders/preview.mp4 --skill hyperframes  # in the background
python3 -I tools/check_film.py renders/preview.mp4 --project . --sheet review/sheet.png
```
Then run the **full-film critic** and **verify critic** (fresh subagents each round, prompts and pass bar in
`review-loop.md`). Stop after 3 film critics and show the user the open items rather than looping. Write
`REVIEW.md` only for honest notes on what was measured versus only looked at.

### 7. Render and deliver
```bash
npx hyperframes render -o renders/<name>.mp4 --quality delivery --skill hyperframes   # run in background
python3 -I tools/check_film.py renders/<name>.mp4 --project . --json
python3 -I tools/check_facts.py --project . --credits out/      # pinned-comment.txt + caption-draft.txt
```
Hand over the MP4, the cover PNG, the post text and the pinned comment. Report the measurements, what nobody
listened to or watched, the weakest shot, and that the AI-content label should be switched on. For news:
re-fetch the primary source right before render, then
`python3 -I <skill>/scripts/news_collect.py --mark-covered <story> --video <slug>` (in the news workspace) after
publishing.

## What "good" looks like
- Frame 0 is a readable hook: a title line + the subject already on screen, never black.
- The 3D object is the explanation: every motion is an operation (weights are thread thickness, a vote is a thread
  landing); the twist re-runs the mechanism on the same object.
- One accent colour (amber) reserved for the answer; everything else warm white on near-black.
- Every number traces to the ledger; benchmarks say who measured them; simplified visuals say so.
- Slow camera always moving; scene changes by camera, dissolve or zoom-through only; no move faster than the
  camera_path limits, so `check_film.py` reports 0 whips and 0 hard cuts.
- Text never collides: every readable word is DOM, in its zone, and `hyperframes check` is clean.

Credits for borrowed ideas are in the repo README.
