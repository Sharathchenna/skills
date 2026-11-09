# REVIEW — "Which it?" v2 (Three.js world + HyperFrames)

## How it is built
- `compositions/world.html` (generated from `tools/world.template.html` by `tools/gen2.py`): one Three.js scene
  under the whole 76 s film — reflective floor, rack wall with seeded blinking LEDs, fog, bloom, the sentence as
  eleven glass word panels, attention threads as tubes whose radius is the weight, wavefront pulses, key/query
  tags, the 1,000 x 1,000 field of word tiles stacked in layers. Every frame is `render(t)`; all randomness seeded.
- HTML layers on top: `hookui` (title), `james` (2.5D parallax: photo + cutout move at different rates),
  `paper` (arXiv page, highlight, zoom-through that dissolves into the world), `stageui` (100% bar, readings),
  `scaleui` (counter), `captions` (karaoke, grey → white per word).
- Rebuild: `./tools/build2.sh` (regenerates and re-applies the portrait grades). v1 generator: `tools/gen.py`.

## Creative calls
- Took the reference's structure: real puzzle → a historical figure → mechanism on one worked example → scale → back.
  The recurring object is the glass word panel + amber thread (the reference's clock).
- No hard cuts: hall → James is a dissolve, James → paper a blur swap, paper → hall a zoom through the title into
  a dive-out from the "it" panel, scale → end a camera flight down from the stacked layers.
- One layout (the four-line block) for the whole film; a receding-row layout was tried and dropped — panels bunched
  and became unreadable in a 9:16 frame.

## Measured vs looked at
- `hyperframes check` passes (two size warnings kept: captions live in one file by design; world.html is one scene).
- Frames reviewed at every beat and every seam. Audio levels were measured earlier (voice normalised to −16 LUFS,
  music 0.16 under it); nobody listened to the mix.

## Weakest shots / with more time
- James is 2.5D parallax, not true image-to-video (no head turn). Needs an image-to-video model (treg/Seedance etc.).
- The hook could use a slow light sweep across the panels; percentages above panels are small on a phone.
- Attention weights are illustrative, not from a model run (stated in assets/CREDITS.md).
