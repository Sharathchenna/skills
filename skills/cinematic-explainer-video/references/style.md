# The style, taken apart

The target is the vertical "cinematic explainer" short (e.g. the Google TrueTime / Einstein video this skill was
built from): 9:16, 60–90 s, narrated, dark and photographic, no hard cuts, one recurring object.

## Four kinds of picture, blended

| Layer | In the reference | How to build it here |
| --- | --- | --- |
| 1. Code-built 3D set | server hall, rows of identical clocks, glowing envelope, orange bokeh | **Three.js world composition** (`templates/world.template.html`): fog, reflective floor, a wall with seeded blinking lights, bloom on the brightest points only, a slow camera on eased keyframes. Identical repeated objects with crisp text are the tell that it is 3D, not AI. |
| 2. Archive photo brought to life | Einstein turns his head, satellite drifts, museum clock ticks | Best: an image-to-video model (Seedance, Veo, Kling…). Without one: **2.5D parallax** — `npx hyperframes remove-background photo.jpg -o cut.png`, then the photo and the cutout push at different rates (bg 1.02→1.07, figure 1.00→1.14 plus a small x drift). Credit line bottom-left. |
| 3. Photo plate + code effects | storm photo + drawn train, procedural lightning, rain, grainy wavefront discs | A real image as the plate, code layers on top (SVG/canvas/Three). The wavefront = warm translucent disc, speckled, brighter rim, additive. |
| 4. Graphics and captions | "waiting 5 ms", "2012: ±4 ms → < 1 ms", karaoke captions | HTML/GSAP compositions above the world; captions in one composition, grey unspoken words turning white per word, ~44 px semi-bold, two lines, centred near y ≈ 1214–1270 on 1080×1920. |

## Story shape

1. A real-world puzzle the viewer can solve or feel (hook, with a title line on frame 0).
2. A famous person who hit the same problem (archive photo, quote).
3. The source of the modern answer (paper, patent, product) — highlight the real line on the real page.
4. The mechanism, on ONE worked example, built up one part per narrated phrase.
5. A twist: change one input, watch the mechanism re-route.
6. Scale: from one example to the real size (numbers that are true).
7. Back to the opening picture with the one-line takeaway; hold ≥ 2 s.

One recurring object carries every scene (clocks there; glass word panels + amber threads in the attention example).

## Sound

Voice + a continuous music bed (the reference never drops below −40 dB for more than 0.4 s) + a few effects tied to
visible actions (whoosh on the big moves, a tick on flips and landing numbers). Mix ≈ −14 LUFS, music ~0.16 under a
−16 LUFS voice.

## Transitions (there are no hard cuts)

- 3D → photo: 0.5 s dissolve while the 3D camera keeps moving underneath.
- photo → photo: blur swap (out: opacity→0 + 8 px blur in 0.16 s; in: blur→0).
- page → 3D: zoom through the title (scale ×9, power3.in) while the page fades, revealing the 3D camera diving out
  of the hero object.
- 3D shot → 3D shot: the camera flies; the world never cuts. A cut can hide behind an opaque overlay.
