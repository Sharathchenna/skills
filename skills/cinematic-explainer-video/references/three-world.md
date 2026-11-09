# The Three.js world composition

One standalone composition (`compositions/world.html`, a full HTML document — not a `<template>`) mounted at the
bottom of the stack for the whole film. Every other scene is an HTML layer above it. Pattern copied from the
HyperFrames registry block `glass-hero` (`npx hyperframes add glass-hero` to read it).

## Contract

```html
<div id="world-root" data-composition-id="world" data-start="0" data-duration="76.12" data-width="1080" data-height="1920">
  <canvas id="world-canvas" class="clip" data-start="0" data-duration="76.12" data-track-index="1" width="1080" height="1920"></canvas>
</div>
<script>
  // classic script: clock + timeline + buildReady, registered synchronously
  const clock = { t: 0 }, host = { clock, render: null };
  window.__world = host;
  window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};
  window.__hf.buildReady["world"] = new Promise((r) => (host.ready = r));
  const tl = gsap.timeline({ paused: true });
  tl.to(clock, { t: D, duration: D, ease: "none", onUpdate: () => host.render && host.render(clock.t) });
  window.__timelines["world"] = tl;
</script>
<script type="module">
  import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.184.0/+esm";
  // addons by full URL, each in try/catch with a plain-render fallback:
  // ".../examples/jsm/objects/Reflector.js/+esm", ".../postprocessing/{EffectComposer,RenderPass,UnrealBloomPass,OutputPass}.js/+esm"
  // ... build scene, await fonts (FontFace from assets/fonts/...), build canvas textures ...
  host.render = (t) => { /* pure function of t */ composer ? composer.render() : renderer.render(scene, camera); };
  host.render(host.clock.t); host.ready();
</script>
```

- Host in `index.html`: `<div id="world" data-composition-id="world" data-composition-src="compositions/world.html" ... style="z-index:1">`.
- `renderer.setPixelRatio(1)`, `preserveDrawingBuffer: true`, `NoToneMapping`; keep text materials `toneMapped: false`.
- Everything is a function of `t`: camera from eased keyframes, states from `ramp(t, start, dur)`, blinking lights
  from `hash(index, floor(t*3))`, all randomness from a seeded mulberry32. Never read the previous frame.

## Building blocks in the template

| Piece | How |
| --- | --- |
| Word panel | Group → pivot → front plane (canvas texture: dark glass panel, white Inter 700 text), thin metal box body, back plane rotated π about Y (number vector) and, for the twist word, about X (the replacement word). Flip = rotate the pivot. Tint = `material.color` (white → amber, ×brightness; >1 feeds bloom). |
| Glow | additive radial sprite behind each panel; UnrealBloomPass(strength 0.45, radius 0.45, threshold 0.92) — keep the threshold high or white text blooms into mush. |
| Floor | `Reflector` + a 0.9-opacity dark tint plane over it (faint, sharp reflection). |
| Thread | `TubeGeometry` on a `QuadraticBezierCurve3`; draw-on via `geometry.setDrawRange(0, n*progress)` (Tube indices run along the path). Radius = weight; rebuild only when the cache key (endpoints + radius) changes. Glow = same curve, radius ×3.2, additive, 0.22 opacity. |
| Wavefront pulse | `CircleGeometry` with a speckled warm disc texture, additive, `lookAt(camera)`, scale 0.1→1.2, opacity 0.42→0. |
| Labels / numbers | Sprites with cached canvas textures keyed by text (percentages re-key as they count). |
| Field of thousands | one `InstancedMesh` (additive, per-instance colour as brightness) + `LineSegments` revealed with `setDrawRange`; ripple reveal by distance. Update instance colours only while the field is on screen. |
| Rack wall | box + instanced seams + 1,500 instanced LED quads with seeded colours and blink. Keep the camera on the hall side of it. |
| Camera | list of `{t, p, l}` keys, `power2.inOut` between them; a key with `cut: true` holds until the next key at the same time (hide cuts under an opaque overlay). |

## Layout lessons

- In 9:16, a sentence of panels reads best as a **centred multi-line block** seen from a slow 3/4 dolly. A row
  receding down a hall (like the reference's clocks) bunches far panels into an unreadable cluster.
- Keep the block between y ≈ 400 and 1150 px on screen; captions own y ≈ 1214–1270; the 100% bar / counters sit at
  y 200–420. Lower the camera's look-at target to raise the block in frame.
- Fog density ≈ 0.036 for close shots, ≈ 0.011 for the big overview; animate it with the camera.

## Iterate fast

`node scripts/world_frames.cjs compositions/world.html 0.5,6.9,37.6` renders the world alone in headless Chrome in
seconds (prints page errors). Use it for camera and layout; use `npx hyperframes snapshot --at …` for the composite.
