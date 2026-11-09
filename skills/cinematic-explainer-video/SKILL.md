---
name: cinematic-explainer-video
description: Make a vertical (9:16) cinematic explainer short in the style of viral "how it really works" videos — a code-built Three.js 3D world under the whole film, archive photos with 2.5D parallax, narration with word-highlight captions, animated callouts, music, and no hard cuts — rendered with HyperFrames. Use when the user shares a reference video in this style and asks how to make one, or asks for a narrated 3D explainer / "make a video like this" about a concept (AI, science, engineering, history). Also covers taking a reference video apart before copying its style.
---

# Cinematic explainer video (Three.js world + HyperFrames)

Builds a 60–90 s 1080×1920 narrated explainer: one Three.js 3D set lives under the entire film, photo scenes and
graphics play above it, captions highlight each spoken word, and every transition is a camera move, dissolve or
zoom-through — never a hard cut. Worked example: `examples/attention/` (how attention works in AI, 76 s).

**Depends on:** the `hyperframes` skill and CLI (`npx hyperframes`; read `/hyperframes` for the composition
contract), `media-use` (for music/SFX/cutouts), `ffmpeg`, Python 3, Node. Voice: Fish Audio API key (free model)
or any TTS. Optional: an image-to-video model for truly animated archive photos.

Read `references/style.md` first (what the look is made of), then `references/three-world.md` before touching the
3D, and `references/pitfalls.md` before reviewing.

## Workflow

### 1. Take the reference apart (if the user gave one)
`sh scripts/analyze_reference.sh <video> ref/` → contact sheets, hard/soft cut detection, loudness, silences,
full-res frames. Then dense strips around each transition. Classify every shot into the four layers of
`references/style.md` (3D set / animated archive photo / photo + code effects / graphics). Tell the user what you
found and which parts need tools they may not have (image-to-video for moving faces).

### 2. Story
One idea, one worked example, one recurring object. Follow the 7-beat shape in `references/style.md`. Write
`STORYLINES.md` (three options; recommend one) unless the user said "you choose" — then pick and say so.
Write `SCRIPT.json`: `[{ "id": "hook", "text": "…" }, …]`, ~8 scenes, ≤ 26 words each, ~145 words total.
Every fact on screen must be sourced; mark illustrative numbers as illustrative.

### 3. Project, voice, timing
```bash
npx hyperframes init <dir> --example blank --resolution portrait --non-interactive --skill hyperframes
cd <dir> && mkdir -p tools && cp <skill>/scripts/* tools/
FISH_API_KEY=… python3 tools/fish_tts.py SCRIPT.json          # or --key-file <file>; never echo the key
python3 tools/build_timeline.py                                # transcribe + loudnorm + timeline.json
python3 tools/word_index.py                                    # indices to wire anchors to words
```
Ask for the API key through the host's secret prompt, never in chat. Check each transcript against the script.

### 4. Assets
Archive photos from Wikimedia Commons (public domain / CC0 / CC BY; record the credit), documents rendered from
their real PDF (PyMuPDF), cutouts with `npx hyperframes remove-background`, a CC0 music bed (Openverse or the
media-use catalog), 2–4 sound effects tied to visible actions. Copy fonts into `assets/fonts/` and declare them
with `@font-face` (bundled Inter/JetBrains Mono files live in the hyperframes package's frame-presets).

### 5. Build
- `compositions/world.html` from `templates/world.template.html`: adapt the panels, layouts, threads and camera keys
  to your subject; inject anchors (absolute word times) as JSON. Keep `render(t)` pure.
- HTML layers above it (each a `<template>` scene, **transparent `#root`**): title, photo scenes (parallax),
  document scene (highlight the real line, zoom through the title into the world), callout UI (bars, counters,
  readings), and one `captions` composition.
- `index.html`: world host at z-index 1 for the whole film, layers above, captions at z 20, one `<audio>` per voice
  scene, SFX and the music bed (volume ~0.16, fades).
- Generate it all from a script (see `examples/attention/tools/gen2.py`) so timing changes are one re-run.

### 6. Review (do not skip)
```bash
npx hyperframes check --json                       # fix every error; weigh warnings
node tools/world_frames.cjs compositions/world.html 0.5,6.9,37.6   # world alone, fast
npx hyperframes snapshot --at <every beat and both sides of every seam> --no-end
```
Tile frames into one sheet with ffmpeg and look: captions never overlap the 3D block, nothing clipped at frame
edges, the camera never behind a wall, glow not eating text, each seam continuous. Write `REVIEW.md`.

### 7. Render and deliver
```bash
npx hyperframes render -o renders/<name>.mp4 --quality delivery --skill hyperframes   # run in background
ffmpeg -hide_banner -i renders/<name>.mp4 -af ebur128=peak=true -vn -f null - 2>&1 | grep -E "I:|Peak"
```
Check a contact sheet of the actual MP4. Report what was measured vs only looked at (nobody listened to the mix),
the weakest shot, and credits (CC BY sounds/images must be credited where published).

## What "good" looks like (from the reference)
- Frame 0 is a readable hook: a title line + the subject already on screen, never black.
- The 3D object is the explanation: weights are thread thickness, flips reveal what the machine sees, the twist
  re-routes the threads on screen.
- One accent colour (amber) reserved for the answer; everything else warm white on near-black.
- Captions: grey → white per word, no box, ~44 px semi-bold, two lines max.
- Slow camera always moving; scene changes by camera, dissolve or zoom-through only.
