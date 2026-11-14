# Example: Diffie–Hellman (CS concept mode, 48.7 s)

Made in Video Studio on autopilot, then rebuilt by hand after review: "the voice is very good, the video looks
vibecoded: text overlaps, the animation isn't smooth, the background isn't great". The files here are the
rebuild. Media (voice, music, fonts) is not included.

| | First cut (Video Studio) | Rebuild |
| --- | --- | --- |
| Labels | WebGL sprites; `hyperframes check` couldn't see them, so "Alice" sat on the caption and equations ran into the "spy" label | DOM labels via `placeLabels`, clamped to the stage zone, no overlaps; `hyperframes check --samples 40` clean |
| Camera | keys 0.5–1 s apart across 4–5 units | `camera_path` spline, max 1.9 units/s and 11°/s |
| `check_film.py` motion | 5 whips (peak frame change 12.9–15.4) | 0 whips, 0 hard cuts (v3 peak 5.6) |
| Set | black void, starfield, grid floor, square dust | v2: gradient backdrop + stone tabletop (still "not great"); **v3: black-glass studio**: softbox environment, satin floor with baked light pools fogged into a void, contact shadows, soft bokeh, ACES, grain + vignette, 30° lens with zoom close-ups (`references/backgrounds.md`) |
| Zones | captions at y 1190–1312 (outside every platform's clear band) | header 288–480, stage 480–1010, captions 1040–1248 at 660 px |

- `tools/gen.py`: anchors from word times, the camera keys (sampled with a Hermite spline inside the file; the
  skill's `scripts/camera_path.py` is the reusable version), every HTML layer, captions and `index.html`.
- `tools/world.template.html`: the pots, paint, orbs, the set and the DOM labels.
  `templates/world-studio.template.html` is the generic version of the same set.
- `PLAN.json`, `quiz.json`, `SCRIPT.json`, `facts/`: the planning card, the 4-question quiz, the script with fact ids,
  and the ledger.
