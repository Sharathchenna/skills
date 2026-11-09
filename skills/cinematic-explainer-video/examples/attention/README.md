# Example: "Which it?" — how attention works in AI (76 s, 1080×1920)

The project this skill was distilled from. Files are the real build inputs; media assets are not committed
(see `CREDITS.md` for every source so they can be re-fetched).

| File | Role |
| --- | --- |
| `SCRIPT.json` | narration, one entry per scene |
| `timeline.json` | output of `build_timeline.py` (scene starts, absolute word times) |
| `STORYLINES.md`, `SPEC.md`, `REVIEW.md` | story options, the v1 spec, the v2 review notes |
| `tools/gen.py` | v1 generator (2D); v2 reuses its caption, paper and scene helpers |
| `tools/gen2.py` | v2 generator: world + overlays + captions + index.html |
| `tools/build2.sh` | runs gen2.py, then applies the portrait grades with `media-treatment` |
| `tmp/*.json` | Inter 700 glyph widths (for v1 layout), SFX and music placement plans |
| `../../templates/world.template.html` | the Three.js world (copy to `tools/world.template.html`) |

## Rebuild
1. `npx hyperframes init` a portrait project, copy this folder's files in, and copy
   `templates/world.template.html` to `tools/world.template.html`.
2. Fetch the assets listed in `CREDITS.md` into `assets/` (`img/`, `music/`, `sfx/`, `fonts/`), generate the voice
   with `scripts/fish_tts.py` and run `scripts/build_timeline.py` (or keep `timeline.json` if you reuse the same takes).
3. `npx hyperframes remove-background assets/img/william-james.jpg -o assets/img/william-james-cut.png`
4. `./tools/build2.sh && npx hyperframes check && npx hyperframes render -o renders/attention.mp4 --quality delivery`

Scenes: hook (3D panels, "What does 'it' mean?") → William James 1890 (parallax portrait + quote) → the 2017 paper
(real abstract line highlighted, zoom through the title) → mechanism in 3D (query pulse, key tags, threads by
weight, value bead, 100% bar) → twist ("tired." flips to "wide.", threads swing to "street") → scale (every word to
every word, 1,000 × 1,000 field, stacked layers) → back to the sentence.
