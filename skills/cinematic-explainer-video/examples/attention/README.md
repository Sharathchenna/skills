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

## Known issues (found after publishing, by the rules added later)

This example predates `platform.md`, `writing.md` and the fact ledger, and breaks a few of them. Fix these if you
reuse its generators:
- The hook title sits at `top: 210px`, under the Reels top bar and outside the profile-grid crop. Move it to ≈ 300.
- The William James quote spans x 90–990, under the like/comment column. Cap it at 774 px wide, centred.
- Captions have no max width. Cap them at 774 px, centred.
- The narration uses colons ("wrote: everyone knows…", "was called: Attention Is All You Need").
- There is no `facts/` ledger; the weights are illustrative and should carry an on-screen "illustrative" tag.
- The music bed ends at the same level it plays; fade it into a 3–4 s silent hold.
- `check_film.py` finds a near-black dip at 10.27–10.43 s (the hook → William James seam): the world fades before
  the photo arrives. Overlap the dissolve so the photo is already in when the world dims.
- From about 33 s the right-hand word panels cross x 927 into the button column. Pull the camera back or narrow
  the block.
