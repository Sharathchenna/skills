# Backgrounds and sets that look expensive

Research into how pmndrs/drei, three.js's own examples, pmndrs/postprocessing and HyperFrames' `product-turntable`
block build studio scenes, done after viewers called a flat gradient-and-tabletop set "not great". The result is in
`templates/world-studio.template.html` ("black-glass studio") and the Diffie–Hellman example.

## What we use by default, and what we learned applying it

| Piece | Setting | Lesson |
| --- | --- | --- |
| Environment | emissive softbox panels (two tall strips, ceiling, a cool ring, a thin front strip) → `PMREMGenerator.fromScene(env, 0.04)` | This is what makes dark metal look like metal. Pots: `MeshPhysicalMaterial` metalness 1, roughness 0.28, clearcoat 0.6 |
| Lens + camera | 30° vertical FOV, ~13 units back, pitched ~20° down; close-ups are **zooms** (FOV down to ~10°) from the wide position | With a long lens looking down, **the floor is the background**: light the floor, don't build a wall nobody sees. Dollying in put the front pots between camera and subject, sliced at the frame edge |
| Floor | one 200×200 satin plane (`0x100e12`, roughness 0.5, metalness 0.2, dithering) | Fog it into a void of the same colour (`Fog(0x060508, 12, 26)`), so there is no horizon line |
| Light pools | baked into an additive radial-gradient plane on the floor: warm behind the hero, soft white under it | Spotlights did the same job but put hot specular flashes on the glossy metal that bloomed into blinking blobs as the camera moved |
| Shadows | contact shadows (depth from below, blurred twice), updated every frame | Hide sprites, points, additive and transparent objects during the depth pass or particles cast blobs |
| Depth | seeded round bokeh discs, size from a thin-lens circle of confusion, additive | Hard-edged hexagons looked cheap; soft round discs with a faint rim read as lens bokeh |
| Tone | ACES Filmic, exposure 1.2 | AgX washed the saturated paint out. `OutputPass` tone-maps the whole buffer, so `toneMapped:false` doesn't protect anything in a composer |
| Bloom | `UnrealBloomPass(0.75, 0.6, threshold 1.0)` in a half-float target with MSAA 4 | Only HDR (> 1) values bloom: glowing things use `color × 3`, `toneMapped:false` |
| Grade | one shader pass after `OutputPass`: vignette + 1.5 px grain seeded by `round(t × 30)` | Grain also stops banding in dark gradients at TikTok bitrates. Never call `composer.render()` without an argument |

Things that are **not** deterministic and must not be used as shipped: `TAARenderPass`, `AfterimagePass`, stock
`FilmPass`, pmndrs `EffectPass` time, SSAO/SAO/GTAO kernels built with `Math.random`, drei `AccumulativeShadows`.

Alternative looks (section 3 below): **Bokeh void** (graphic gradient + bokeh, no room; best for text-heavy films) and
**Alchemist's workshop** (warm, practical, out-of-focus shelves).

---

## 0. Diagnosis: why the current background looks cheap

The current build is a gradient backdrop shader, a warm glow, a fogged stone tabletop, a small Reflector mirror, a halo sprite, dust motes and a CSS vignette. It is missing three things that every high-end example below has:

1. **Nothing for the metal to reflect.** Dark metal only looks like metal when it reflects bright, shaped highlights. That is why pmndrs, model-viewer, three's RoomEnvironment and HyperFrames' own `product-turntable` all build an *environment made of softboxes*. A gradient backdrop does not light the pots. Without IBL (image-based lighting), the pots read as grey plastic.
2. **No grounding.** A mirror with no blur reads as a CG hack. Every pmndrs product demo uses a soft contact shadow (ContactShadows or AccumulativeShadows) and keeps any reflection blurred (MeshReflectorMaterial `blur=[400,100]`, `mixBlur`).
3. **No seamless horizon.** A table edge plus a gradient wall gives two visible planes and a seam. Studios use a curved cyclorama (drei `Backdrop`), or no floor at all and a fog-matched void.

The finishing layer (AgX tone mapping, bloom that only hits HDR emissives, grain that also dithers away banding in dark gradients, and MSAA) is what separates "nice" from "expensive".

---

## 1. Ranked techniques with sources and vanilla recipes

### #1. A studio environment built from softbox "lightformers" (IBL), with no HDRI file
**Sources**
- `mrdoob/three.js examples/jsm/environments/RoomEnvironment.js`. A Scene with a BackSide box room, 6 instanced boxes and 6 "area light" boxes. Their material is `MeshBasicMaterial` with colour multiplied by 17–100, so the values are above 1 (HDR). The doc comment says to use it via `new PMREMGenerator(renderer).fromScene(new RoomEnvironment()).texture` and assign the result to `scene.environment`. It is based on Google model-viewer's EnvironmentScene.
- `pmndrs/drei src/core/Lightformer.tsx`. Just a `planeGeometry` / `ringGeometry` with `meshBasicMaterial`, colour times `intensity`, `toneMapped=false`, `DoubleSide`, and `lookAt(target)`.
- `pmndrs/drei src/core/Environment.tsx` (`EnvironmentPortal`). Children go into a *virtual Scene*, a `CubeCamera` renders it into a `WebGLCubeRenderTarget(resolution=256)` with `type=HalfFloatType`, and the texture becomes `scene.environment`. The default is `frames=1`, i.e. rendered once.
- `pmndrs/examples examples/building-live-envmaps/src/App.jsx`. This is the famous Porsche "Lightformers" demo. Its rig: a ceiling rect (intensity 0.75, scale 10x10), 8 circle strips at intensity 2 that slide along z, side strips of `scale [20,0.1]` at intensity 4, a red accent ring, and a BackSide sphere with a dark grey and blue depth gradient as the env "walls".
- drcmda on the three.js forum ("R3F Lightformers in vanilla three js"): "you do not need pmrem.fromScene, just a regular cubecamera".
- In three r184, `CubeCamera.update()` sets `renderTarget.texture.needsPMREMUpdate = true` (checked in `src/cameras/CubeCamera.js`), so a CubeCamera texture used as `scene.environment` gets PMREM-filtered automatically.
- **HyperFrames registry `product-turntable`** (heygen-com/hyperframes `registry/blocks/product-turntable/product-turntable.html`) does exactly this with three@0.184 from jsDelivr. It dims a RoomEnvironment's lights to 0.3x, adds two emissive strip softboxes (key at -35° with intensity 5, rim at 120° with intensity 8), calls `pmrem.fromScene(studio, 0.02)`, and uses ACES at exposure 1.3.

**Vanilla recipe (static, render once, deterministic)**
```js
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

function lightformer(scene, { w, h, pos, color = 0xffffff, intensity = 1, form = 'rect', target = [0, 1, 0] }) {
  const geo = form === 'ring' ? new THREE.RingGeometry(0.35, 0.5, 64)
            : form === 'circle' ? new THREE.CircleGeometry(0.5, 64)
            : new THREE.PlaneGeometry(1, 1);
  const mat = new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, toneMapped: false });
  mat.color.multiplyScalar(intensity);              // HDR > 1, same trick as drei/RoomEnvironment
  const m = new THREE.Mesh(geo, mat);
  m.scale.set(w, h, 1); m.position.set(...pos); m.lookAt(...target);
  scene.add(m); return m;
}

const env = new THREE.Scene();
env.background = new THREE.Color(0x050407);         // near-black studio walls, so contrast stays high
lightformer(env, { w: 1.2, h: 8, pos: [-5, 2, 3],  intensity: 6 });                    // tall key strip (left)
lightformer(env, { w: 1.2, h: 8, pos: [ 5, 2, -3], intensity: 9, color: 0xffe6c8 });  // warm rim strip (back right)
lightformer(env, { w: 8,   h: 8, pos: [0, 7, 0],  intensity: 1.2 });                  // soft ceiling
lightformer(env, { w: 3, h: 3, pos: [-6, 1, -6], intensity: 3, color: 0x2a6bff, form: 'ring' }); // cool accent ring (shows as a ring glint on metal)
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(env, 0.04).texture;   // sigma 0.02–0.04 softens the strips
scene.environmentIntensity = 1.0;                          // r163+
// metal pots: MeshPhysicalMaterial({ color: 0x1a1a1f, metalness: 1, roughness: 0.28, clearcoat: 0.6, clearcoatRoughness: 0.15 })
```
**Animated variant** (for example a light strip sweeping across the pots on a beat): keep `env` as a separate scene, move the strip from `t`, and either call `pmrem.fromScene(env)` each frame, or use `const cubeRT = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType }); const cubeCam = new THREE.CubeCamera(0.1, 100, cubeRT); scene.environment = cubeRT.texture;` and call `cubeCam.update(renderer, env)` inside `render(t)`. This stays deterministic because the env is a pure function of t. The pmndrs demo's `group.position.z += delta*10` is **not** deterministic. Replace it with `z = ((t*10 + 60) % 80) - 60`.

**Cost:** once at init, about 6 cube faces at 256² plus the PMREM blur: negligible. Per-frame animated: about 6 tiny renders plus PMREM, roughly 1–3 ms on a GPU.

### #2. Contact shadows instead of the mirror (with an optional blurred reflection)
**Sources**
- `pmndrs/drei src/core/ContactShadows.tsx`, which is based on mrdoob's `examples/webgl_shadow_contact.html`. The steps: an orthographic camera looks up from the floor; the scene renders once with `scene.overrideMaterial = MeshDepthMaterial` (patched so `alpha = 1 - fragCoordZ`, giving a darker shadow nearer the floor) into a 512² target; a Horizontal then Vertical blur runs (`h = blur/256`), twice when `smooth`; the result goes on a transparent plane, flipped with `scale [1,-1,1]`. Defaults are `far=10, blur=1, resolution=512`. The `backdrop-and-cables` demo uses `scale=5 blur=1.5 far=1`.
- `AccumulativeShadows.tsx` / `RandomizedLight` give ray-traced-looking soft shadows by jittering a shadow-casting light with `Math.random()` over N frames into a ProgressiveLightMap. Its vanilla twin is `three/addons/misc/ProgressiveLightMap.js`.
- `MeshReflectorMaterial.tsx`: a mirror render, then a depth-aware `BlurPass`, then mixing. The `ground-reflections-and-video-textures` demo uses `blur=[400,100] resolution=512 mirror=0.5 mixBlur=6 mixStrength=1.5 metalness=0.4` plus a roughness map. The lesson: if you keep a reflection, it must be blurred and broken up by roughness.
- `product-turntable` (HyperFrames) simply puts a radial-gradient CanvasTexture under the object at `rgba(0,0,0,0.55)` fading to 0. Its comment: "soft baked contact shadow: no shadow maps, no per-frame cost."

**Vanilla recipe (port of ContactShadows)**
```js
import { HorizontalBlurShader } from 'three/addons/shaders/HorizontalBlurShader.js';
import { VerticalBlurShader }   from 'three/addons/shaders/VerticalBlurShader.js';
function makeContactShadows(renderer, scene, { size = 4, far = 1.2, res = 512, blur = 2.5, opacity = 0.85 } = {}) {
  const group = new THREE.Group();
  const rt = new THREE.WebGLRenderTarget(res, res), rtB = new THREE.WebGLRenderTarget(res, res);
  rt.texture.generateMipmaps = rtB.texture.generateMipmaps = false;
  const geo = new THREE.PlaneGeometry(size, size).rotateX(Math.PI / 2);
  const plane = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: rt.texture, transparent: true, opacity, depthWrite: false }));
  plane.scale.y = -1; plane.renderOrder = 1; group.add(plane);
  const blurPlane = new THREE.Mesh(geo); blurPlane.visible = false; group.add(blurPlane);
  const cam = new THREE.OrthographicCamera(-size/2, size/2, size/2, -size/2, 0, far);
  cam.rotation.x = Math.PI / 2; group.add(cam);
  const depthMat = new THREE.MeshDepthMaterial(); depthMat.depthTest = depthMat.depthWrite = false;
  depthMat.onBeforeCompile = s => { s.fragmentShader = s.fragmentShader.replace(
    'vec4( vec3( 1.0 - fragCoordZ ), opacity );', 'vec4( vec3( 0.0 ), ( 1.0 - fragCoordZ ) * 1.0 );'); };
  const hB = new THREE.ShaderMaterial(HorizontalBlurShader), vB = new THREE.ShaderMaterial(VerticalBlurShader);
  hB.depthTest = vB.depthTest = false;
  const blurOnce = (amt) => {
    blurPlane.visible = true;
    blurPlane.material = hB; hB.uniforms.tDiffuse.value = rt.texture;  hB.uniforms.h.value = amt / 256;
    renderer.setRenderTarget(rtB); renderer.render(blurPlane, cam);
    blurPlane.material = vB; vB.uniforms.tDiffuse.value = rtB.texture; vB.uniforms.v.value = amt / 256;
    renderer.setRenderTarget(rt);  renderer.render(blurPlane, cam);
    blurPlane.visible = false;
  };
  group.update = () => {                       // call inside render(t) BEFORE the main render (or once, if nothing moves)
    const bg = scene.background; scene.background = null; plane.visible = false;
    scene.overrideMaterial = depthMat;
    renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(scene, cam);
    scene.overrideMaterial = null; blurOnce(blur); blurOnce(blur * 0.4);
    renderer.setRenderTarget(null); plane.visible = true; scene.background = bg;
  };
  return group;   // place it at floor height, e.g. group.position.y = 0.001
}
```
Hide the glowing orbs, dust and halo from the depth pass (`obj.visible = false` during `update`). Otherwise particles cast shadow blobs.

**AccumulativeShadows, made deterministic:** replace `Math.random` with a seeded PRNG (`mulberry32`), then run the accumulation *at init*, for example 64–100 iterations before the first frame, **non-temporal**. The result is a baked, static lightmap. It is only valid while the pots do not move relative to the floor.

### #3. A curved cyclorama (or a fog-matched void) with a pool of light behind the subject
**Sources**
- `pmndrs/drei src/core/Backdrop.tsx` (41 lines). A `PlaneGeometry(1,1,segments,segments)` with vertices rewritten so `z = easeInExpo(x/segments)`, where `easeInExpo = x => x===0 ? 0 : 2**(10x-10)`. The first row is pushed by `-floor` to extend the floor, then the mesh is rotated `[-PI/2, 0, PI/2]`. `backdrop-and-cables` uses `floor=2 position=[0,-0.5,-3] scale=[50,10,4]` with `meshStandardMaterial color="#353540" envMapIntensity=0.1`, a coloured spotLight with `penumbra=1` (`#0c8cbf`) and a red directional rim.
- drei `Stage.tsx` lighting presets, positions multiplied by the subject's radius: `rembrandt main [1,2,1] fill [-2,-0.5,-2]`, `portrait main [-1,2,0.5]`, `upfront main [0,2,1]`, `soft main [-2,4,4]`. Main is a spotLight with `penumbra 1`, `intensity*2`; fill is a pointLight at `intensity`; plus an ambient at `intensity/3`.
- The pmndrs `bloom-hdr-workflow-gltf` demo and the reflections demo match `<color background>` to `<fog>` (`#202030`, fog 10→25; and black, fog 15→20). That makes the floor dissolve into the void with no horizon.

**Vanilla recipe**
```js
function backdrop({ floor = 1.5, segments = 32 } = {}) {
  const g = new THREE.PlaneGeometry(1, 1, segments, segments), p = g.attributes.position;
  const ease = x => (x === 0 ? 0 : Math.pow(2, 10 * x - 10)), off = 0.5; let i = 0;
  for (let x = 0; x <= segments; x++) for (let y = 0; y <= segments; y++)
    p.setXYZ(i++, x / segments - off + (x === 0 ? -floor : 0), y / segments - off, ease(x / segments));
  p.needsUpdate = true; g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x14121a, roughness: 0.9, metalness: 0, dithering: true }));
  m.rotation.set(-Math.PI / 2, 0, Math.PI / 2);
  const grp = new THREE.Group(); grp.add(m); return grp;
}
const cyc = backdrop(); cyc.scale.set(14, 10, 9); cyc.position.set(0, 0, -3); scene.add(cyc); // 9:16 needs it TALL (z scale = wall height)
// "background light": a soft spot grazing the cyc behind the pots gives a physically consistent halo (replaces the sprite)
const bgSpot = new THREE.SpotLight(0xff9a4a, 60, 20, 0.5, 1, 2); bgSpot.position.set(0, 1, 2); bgSpot.target.position.set(0, 2.5, -6);
scene.add(bgSpot, bgSpot.target);
scene.fog = new THREE.Fog(0x0b0a10, 8, 18); // same colour as renderer clear colour, so the top of the frame fades to the void
```
In 9:16 the camera sees a lot of floor and a lot of sky. Use a long lens (fov 20–28°, as the turntable uses 24°) and pitch the camera down slightly, so the cyc curve sits at about 40% of frame height behind the pots.

### #4. HDR emissives plus selective-by-threshold bloom, AgX tone mapping, and MSAA
**Sources**
- `pmndrs/postprocessing` (v6.39.6, released 2026-11-01, peer dep `three >= 0.168 < 0.188`, so it works with 0.184). `BloomEffect` defaults: `luminanceThreshold 1.0, luminanceSmoothing 0.03, mipmapBlur true, radius 0.85, levels 8`. `ToneMappingEffect` default `mode = AGX`. `VignetteEffect` `offset 0.5, darkness 0.5`. `NoiseEffect` `premultiply` option. The README recommends `new WebGLRenderer({ antialias:false, stencil:false, depth:false })` and `EffectComposer(renderer, { frameBufferType: HalfFloatType })` to avoid banding in dark scenes.
- pmndrs docs and the three.js forum: "you don't need select bloom, it is selective by default, all you have to do is increase color intensity". Use threshold 1 and `color` / `emissiveIntensity` above 1 with `toneMapped:false`.
- three `webgl_postprocessing_unreal_bloom_selective.html` (layers, darkMaterial swap, mix ShaderPass). This is the fallback if the threshold trick catches unwanted highlights.
- three constants: `AgXToneMapping = 6`, `NeutralToneMapping = 7`, both present in r184. The three examples still use ACES (`webgl_postprocessing_unreal_bloom`, `product-turntable` at exposure 1.3). AgX desaturates highlights more gracefully, which suits saturated glowing paint.

**Vanilla recipe (three's own passes, no new dependency)**
```js
renderer.toneMapping = THREE.AgXToneMapping; renderer.toneMappingExposure = 1.1; // applied by OutputPass
const rt = new THREE.WebGLRenderTarget(1080, 1920, { type: THREE.HalfFloatType, samples: 4 }); // MSAA inside the composer
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(1080, 1920), 0.9 /*strength*/, 0.6 /*radius*/, 1.0 /*threshold, linear HDR*/);
composer.addPass(bloom);
composer.addPass(new OutputPass());          // tone map + sRGB happens here
composer.addPass(gradePass);                 // grain + vignette, see #6 (display-space)
// paint: MeshStandardMaterial({ color: 0x000000, emissive: paintColor, emissiveIntensity: 4 }) (only it crosses 1.0)
// orbs:  MeshBasicMaterial({ color: new THREE.Color(paintColor).multiplyScalar(3), toneMapped: false })
// ALWAYS: composer.render(0) or composer.render(1/30). Never call it with no argument (it reads a wall-clock Timer).
```
**pmndrs/postprocessing alternative** (better mipmap bloom, built-in Vignette/Noise/AgX/SMAA in a single merged pass). Use an importmap so it shares *your* three instance. Do not use jsDelivr `+esm` for it: `+esm` bundles its own three. The `build/index.js` file does `import … from "three"`:
```html
<script type="importmap">{ "imports": {
  "three": "https://cdn.jsdelivr.net/npm/three@0.184.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.184.0/examples/jsm/",
  "postprocessing": "https://cdn.jsdelivr.net/npm/postprocessing@6.39.6/build/index.js" } }</script>
```
```js
import { EffectComposer, RenderPass, EffectPass, BloomEffect, ToneMappingEffect, ToneMappingMode,
         VignetteEffect, NoiseEffect, BlendFunction, SMAAEffect } from 'postprocessing';
const composer = new EffectComposer(renderer, { frameBufferType: THREE.HalfFloatType, multisampling: 4 });
renderer.toneMapping = THREE.NoToneMapping;      // the ToneMappingEffect does it
composer.addPass(new RenderPass(scene, camera));
const noise = new NoiseEffect({ premultiply: true, blendFunction: BlendFunction.SCREEN }); noise.blendMode.opacity.value = 0.25;
const fx = new EffectPass(camera,
  new BloomEffect({ mipmapBlur: true, luminanceThreshold: 1, luminanceSmoothing: 0.2, intensity: 1.2, radius: 0.75 }),
  new ToneMappingEffect({ mode: ToneMappingMode.AGX }),
  new VignetteEffect({ offset: 0.35, darkness: 0.65 }), noise);
composer.addPass(fx);
// determinism: EffectPass does material.time += deltaTime. Pin it per frame:
function renderFrame(t) { fx.fullscreenMaterial.time = t; composer.render(0); }
```
Keep only one tone mapping in the chain (either `renderer.toneMapping` + OutputPass, or a ToneMappingEffect), and have *all* other materials keep `toneMapped:true`.

### #5. Depth of field (real, or faked bokeh)
**Sources**
- three `examples/jsm/postprocessing/BokehPass.js` (uniforms `focus`, `aperture`, `maxblur`). It re-renders the scene with a depth material into its own target.
- pmndrs `DepthOfFieldEffect` / `BokehEffect` / `TiltShiftEffect`.
- **HyperFrames `rack-focus` block** (registry source): out-of-focus lights are *splatted as aperture-shaped sprites* (6-blade polygon, cat's-eye clipping toward the corners). Size comes from a circle of confusion computed with BokehShader2's thin-lens formula, `c = (d - f) / (d * fstop * CoC)`. The author's note: "A CSS/Gaussian blur softens everything uniformly. A real defocus turns each point of light into an image of the aperture."
- After Effects motion-graphics practice (gradient, then glow, then grain, then vignette, with a Gaussian blur for depth) is the same stack.

**Vanilla recipe (real DOF)**
```js
const bokeh = new BokehPass(scene, camera, { focus: camera.position.distanceTo(potCenter), aperture: 0.004, maxblur: 0.008 });
composer.insertPass(bokeh, 1);   // after RenderPass, before bloom, so blurred highlights bloom like a lens
// animate a rack focus deterministically: bokeh.uniforms.focus.value = lerp(dNear, dFar, ease(t))
```
**Cheaper and more controllable: fake bokeh in the background.** Put 30–80 seeded points behind the pots (warm and cool). Render them as `THREE.Points` with a shader that draws a soft hexagon disc. Set `gl_PointSize = baseSize * coc(depth)` and alpha to `1/size²` (energy conservation, as in rack-focus), with additive blending. Then the pots stay razor sharp and the background reads as an out-of-focus room. This also replaces "dust motes", which look like noise at TikTok bitrates.

### #6. Film grain plus vignette in post (and dithering against banding)
**Sources**
- three `examples/jsm/shaders/FilmShader.js`: `noise = rand(fract(vUv + time))`, intensity default 0.5. **Gotcha:** `FilmPass.render()` does `this.uniforms.time.value += deltaTime`, and `EffectComposer.render()` without an argument uses an internal `Timer`. Both are non-deterministic, so pin the time.
- pmndrs `noise.frag` is `rand(uv * (1.0 + time))`, with the same `time += deltaTime` accumulation in `EffectPass`.
- mattdesl `gl-vignette-background` `frag.glsl`: a radial `smoothstep` vignette between two colours, plus overlay-blended `random(vUv)` noise at `noiseAlpha`. This is the classic "soft WebGL backdrop".
- Motion-graphics guidance: about 3–5% monochrome noise acts as dither on gradients.

**Vanilla recipe (one display-space ShaderPass after OutputPass)**
```js
const GradeShader = { uniforms: { tDiffuse: { value: null }, uFrame: { value: 0 }, uGrain: { value: 0.045 }, uVig: { value: 0.55 }, uAspect: { value: 1080/1920 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uFrame,uGrain,uVig,uAspect; varying vec2 vUv;
    float h(vec3 p){ p=fract(p*vec3(443.897,441.423,437.195)); p+=dot(p,p.yzx+19.19); return fract((p.x+p.y)*p.z); }
    void main(){ vec3 c=texture2D(tDiffuse,vUv).rgb;
      vec2 q=(vUv-.5)*vec2(1.,1./uAspect)*0.75; float v=smoothstep(1.0,0.25,length(q)); c*=mix(1.-uVig,1.,v);
      float n=h(vec3(floor(vUv*vec2(1080.,1920.)/1.5),uFrame))-.5;   // 1.5px grain survives H.264 better than 1px
      c+=n*uGrain*(0.6+0.4*(1.-dot(c,vec3(.299,.587,.114))));          // a little more grain in shadows (film-like)
      gl_FragColor=vec4(c,1.); }` };
const gradePass = new ShaderPass(GradeShader);
// per frame: gradePass.uniforms.uFrame.value = Math.round(t * fps);   // integer frame index gives exact repeatability
```
Also set `dithering: true` on the backdrop and floor materials. Keep the CSS vignette *or* the shader vignette, not both. The shader vignette is better because it applies before grain and before encoding.

---

## 2. Determinism and cost (1080x1920, offline)

| Technique | Deterministic? | How to make it safe | Relative cost/frame |
|---|---|---|---|
| RoomEnvironment / lightformer env (PMREM once) | Yes | Build at init | ~0 (init only) |
| Animated lightformer env (CubeCamera or PMREM per frame) | Yes | Positions derived from `t`, never `+= delta` | Low (6×256² faces plus PMREM) |
| ContactShadows port | Yes | Call `update()` inside `render(t)` (or once if static); hide particles | Low (1 depth render at 512² + 4 tiny blurs) |
| AccumulativeShadows / ProgressiveLightMap | **No** as shipped (`Math.random`, temporal blend) | Seeded PRNG, bake N iterations at init, then freeze | Init-heavy, 0 per frame |
| Blurred reflector (MeshReflectorMaterial-style) | Yes | Mirror render each frame | Medium-high (second scene render + blur) |
| Cyclorama + fog + spot pool | Yes | n/a | ~0 (one spot shadow if you enable it; otherwise none) |
| UnrealBloomPass / pmndrs mipmap Bloom | Yes | `composer.render(0)` | Medium (5 mip levels × blur at HD) |
| AgX / ACES / Neutral tone map | Yes | n/a | ~0 |
| MSAA (`samples: 4`) | Yes | n/a | Low-medium |
| BokehPass DOF | Yes | Focus from `t` | Medium-high (extra depth render + 1 heavy full-screen pass) |
| Fake bokeh sprites | Yes | Seeded positions, `t`-driven drift | Low |
| GTAOPass | **Almost**. `_generateNoise()` uses `new SimplexNoise()`, which defaults to `Math.random` | Construct it while `Math.random` is temporarily replaced by a seeded PRNG; HyperFrames may render chunks in parallel workers, so an unseeded kernel can differ between chunks | High (several full-res passes) |
| SSAOPass / SAOPass | **No** (`Math.random` kernel/noise) | Same seeding trick | High |
| TAARenderPass / any temporal AA, AfterimagePass | **No** (accumulates previous frames) | Avoid; use MSAA or supersampling | n/a |
| FilmPass (stock) | **No** (`time += deltaTime`) | Use the custom grade pass with `uFrame` | ~0 |
| pmndrs NoiseEffect / any EffectPass with time | **No** by default | `fx.fullscreenMaterial.time = t; composer.render(0)` | ~0 |
| drei Sparkles port | Yes if attributes are seeded and the `time` uniform is set to `t` | `mulberry32(seed)` for size/speed/noise | Low |

General rules: no `Math.random`, `Date.now`, `performance.now`, `clock.getDelta` or `composer.render()` without a fixed delta. Everything else derives from `t` or a seed. If HyperFrames renders on a software GL path, the "High" rows can mean seconds per frame. Prefer the Low rows and get softness from the env, the fog and fake bokeh, not from GTAO or a second scene render.

---

## 3. Three looks for a 9:16 cryptography explainer with glowing paint pots

### Look A: "Black-glass studio" (dark cyclorama with softbox reflections). Recommended default.
The Apple/Porsche-configurator look: the pots are the only colour, and the metal is defined by long white strip reflections.
- **Palette:** void `#07070A`, cyc `#121118` → `#1B1922` at the light pool, softbox white `#FFF6EC`, rim `#FFD9B0`. Paint: crypto-key blue `#3D7BFF`, secret amber `#FFB020`, mixed teal `#21E6C1`. Orbs share the paint hues.
- **Techniques:** #1 lightformer env (2 tall strips + ceiling + 1 cool ring) · #3 cyc, scaled tall, with a warm `bgSpot` pool behind the centre pot and fog matched to `#07070A` · #2 ContactShadows (`blur 2.5, far 1.2, opacity 0.8`) on a matte floor, *no mirror* · #4 HDR paint (`emissiveIntensity 3–5`), UnrealBloom `0.8/0.6/1.0`, AgX at exposure 1.0 · #6 grain 0.035 and vignette 0.5 · MSAA 4. Optional: the strip lightformer slides slowly across the pots during "encryption" beats (an animated env driven by t).

### Look B: "Bokeh void" (abstract gradient with out-of-focus lights). The Kurzgesagt/3Blue1Brown-style graphic backdrop.
There is no room at all. The pots float on pedestals that fade into a soft gradient, and the depth comes from bokeh discs. Text and diagrams read best on this.
- **Palette:** deep indigo `#0B0B1F` → `#1A1240` (top), with a radial lift `#2B1B5A` behind the subject; bokeh discs in paint hues at 15–30% opacity plus a few warm `#FFC27A`; pedestal tops `#2A2833`.
- **Techniques:** full-screen backdrop quad (a mattdesl-style radial `smoothstep` between two colours, plus a slow t-driven domain-warped low-frequency noise for a "mesh gradient" feel), depthWrite off and rendered first · #5 fake bokeh sprites (hexagonal, CoC-scaled, additive, seeded) in 2–3 depth layers with slow parallax driven by t · #1 a *minimal* env (a RoomEnvironment at 0.3x is enough for the metal) · pedestals fade into fog/gradient, no floor and no shadows · #4 bloom slightly stronger (`1.1/0.75`) · #6 grain 0.05 (needed on smooth gradients to stop banding) · optional BokehPass only for a rack-focus moment.
- HyperFrames-native option: render the gradient in a DOM layer *behind* a transparent WebGL canvas (`alpha:true`, as `product-turntable` does with a CSS radial gradient), using `aurora-drift` / `mesh-gradient-bg` / `grain-overlay`. This is the cheapest and easiest to restyle, but the gradient is then not affected by bloom or fog. Keep the bokeh in WebGL.

### Look C: "Alchemist's cipher workshop" (warm, practical, story-driven)
A dim workbench; the paint is a "secret ingredient". Warmer and more narrative, but more risk of clutter, so keep detail out of focus.
- **Palette:** walnut and soot `#120C08` → `#2A1A10`, brass `#C89B5A`, candle key `#FFB46B` (2700K feel), cool moonlight fill from a back window `#6F8FD8`. Paint stays saturated so it pops against the warm low-chroma surround.
- **Techniques:** #1 env with one big warm rect ("window glow") plus one cool rim strip plus a small hot circle (a candle reflection in the pots) · surface: the existing stone/wood table, but rough (roughness 0.7+), with #2 ContactShadows and optionally a *blurred* reflector at low strength (0.15) for wet-stone sheen · background: 2–3 out-of-focus silhouettes (shelves, jars) as simple boxes or cards behind the pots, softened by #5 BokehPass (aperture high enough that they are just shapes) or by fake bokeh for distant "candle" points · fog `#1A110B` · AgX at exposure 0.9 · bloom `0.7/0.5/1.0` · grain 0.05 with stronger vignette (0.65).

All three: long lens (fov 22–30°), pots in the middle third, 15–20% headroom for captions at the top and the TikTok UI at the bottom, and the brightest background value placed directly *behind* the hero pot (a pool of light or radial lift) so the silhouette separates.

---

## 4. HyperFrames registry blocks (from `npx hyperframes catalog --json`, v0.9.45, 448 entries)

Install with `npx hyperframes add <name>`. These are editable source; most are authored at 1920x1080, so re-frame them for 1080x1920.

**Directly useful for this scene**
- `product-turntable` (block, three.js): the reference implementation of the studio recipe on three@0.184 (RoomEnvironment at 0.3x plus emissive strip softboxes via PMREM, ACES at 1.3, baked radial contact shadow, CSS radial-gradient backdrop behind an `alpha` canvas). Read or borrow it even if you don't use the block.
- `grain-overlay` (component): CSS film grain overlay. A quick win, but the WebGL grade pass is preferable when bloom is in play.
- `vignette` (component): pure-CSS radial vignette (already similar to what you have).
- `aurora-drift` (component): three soft accent-derived fields drifting over a deep base with a faint vignette, an "exact ambient loop". A good DOM backdrop for Look B.
- `mesh-gradient-bg` (component): render-safe mesh gradient from animated radial layers (Look B).
- `grain-field` (component): accent-tinted drifting dot field over a luminance gradient (Look B texture).
- `rack-focus` (block, WebGL): real aperture-bokeh splats with a CoC model. Steal the sprite shader for fake bokeh, and use it for a focus-pull moment.
- `vfx-anamorphic-flare` (block): drifting bright points with anamorphic streaks. Use sparingly on orbs or "key" moments.
- `starfield` (block): seek-safe parallax twinkle. Could stand in for "data motes" in Look B.
- `glass-hero` (block, three.js): glass refraction in front of a headline. Possibly useful for a "cipher text through glass" title.
- `extruded-logo`, `exploded-stack` (three.js): title cards and layer diagrams (e.g. encryption layers) in the same 3D language.

**Shader backdrops (WebGPU, from shaders.com, MIT).** Check that WebGPU works in your headless render before relying on these: `mesh-gradient`, `flowing-gradient`, `swirl`, `blob`, `godrays`, `fractal-noise`, `lens-flare`, `aurora`, `plasma`. Object shaders such as `chrome-orb`, `obsidian`, `liquid-metal` and `thin-film` show material looks for the orbs.

**Transitions worth having:** `light-leak`, `organic-light-leak-overlay`, `cinematic-zoom`, `chromatic-radial-split`.

---

## 5. Quick integration plan for the current scene
1. Delete the gradient backdrop shader, halo sprite and Reflector. Add the lightformer env (#1) and set the pots to metalness 1, roughness 0.25–0.35, with a clearcoat.
2. Add the cyclorama plus fog-matched void and a background spot pool (#3). Floor = the cyc's floor, matte.
3. Add ContactShadows (#2), hiding orbs and dust from its depth pass.
4. Composer: HalfFloat with MSAA 4 → (optional BokehPass) → UnrealBloom threshold 1.0 → OutputPass with AgX → grade pass (grain + vignette). Paint and orbs use HDR emissive. Remove the CSS vignette.
5. Replace dust motes with seeded fake-bokeh sprites.
6. Audit: grep for `Math.random|Date.now|getDelta|performance.now|composer.render()` and replace them all with t or seed derivations.

## Sources
- pmndrs/drei source: `src/core/{Environment,Lightformer,ContactShadows,AccumulativeShadows,Stage,Backdrop,Sparkles,softShadows,MeshReflectorMaterial}.tsx`. Docs: https://drei.docs.pmnd.rs/staging/environment
- pmndrs/examples: `examples/{building-live-envmaps,backdrop-and-cables,baking-soft-shadows,ground-reflections-and-video-textures,staging-and-camerashake,bloom-hdr-workflow-gltf}/src/App.jsx`. https://github.com/pmndrs/examples
- mrdoob/three.js: `examples/jsm/environments/RoomEnvironment.js`; `examples/jsm/postprocessing/{FilmPass,BokehPass,GTAOPass,SSAOPass,SAOPass,TAARenderPass,UnrealBloomPass,EffectComposer}.js`; `examples/jsm/shaders/FilmShader.js`; `examples/jsm/objects/Sky.js`; `examples/webgl_postprocessing_unreal_bloom{,_selective}.html`, `webgl_shadow_contact.html`, `webgl_materials_physical_transmission.html`; `src/cameras/CubeCamera.js`; `src/constants.js`
- pmndrs/postprocessing v6.39.6: `src/effects/{Bloom,Noise,Vignette,ToneMapping,DepthOfField}Effect.js`, `src/passes/EffectPass.js`, `src/materials/EffectMaterial.js`, README, package.json. https://github.com/pmndrs/postprocessing
- three.js forum: [R3F Lightformers in vanilla three js](https://discourse.threejs.org/t/r3f-lightformers-in-vanilla-three-js/48495), [lightformers discussion](https://discourse.threejs.org/t/more-natural-ways-to-see-any-objects-with-lightformers-of-environments/47684), [Selective bloom](https://discourse.threejs.org/t/selective-bloom-on-jsx-model/48352)
- [react-postprocessing Bloom docs](https://react-postprocessing.docs.pmnd.rs/effects/bloom)
- heygen-com/hyperframes: `registry/blocks/product-turntable/product-turntable.html`, `registry/blocks/rack-focus/rack-focus.html`; catalog via `npx hyperframes catalog --json`
- [mattdesl/gl-vignette-background](https://github.com/mattdesl/gl-vignette-background) (`frag.glsl`)
- Stripe-style mesh gradient: [jordienr/whatamesh](https://github.com/jordienr/whatamesh), [bram.us write-up](https://www.bram.us/2021/10/13/how-to-create-the-stripe-website-gradient-effect/)
- Remotion 3D determinism: [ThreeCanvas docs](https://www.remotion.dev/docs/three-canvas), [@remotion/three](https://www.remotion.dev/docs/three)
- Three.js Journey "Realistic render" lesson notes: [zhuzi.dev](https://zhuzi.dev/posts/threejs-journey-notes-5-advanced-techniques-part3/)
- Motion-graphics backdrop stack: [Adobe Video World, gradient backgrounds](https://adobevideoworld.com/gradient-background-after-effects/)
- Bruno Simon [folio-2025](https://github.com/brunosimon/folio-2025) (WebGPU/TSL; techniques not inspected in depth)
