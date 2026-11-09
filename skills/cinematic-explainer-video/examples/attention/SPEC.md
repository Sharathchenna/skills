# SPEC — "Which it?" (how attention works in AI)

GOAL:    the viewer leaves knowing attention = every word asking every other word "are you the one I need?",
         shown on one real sentence whose meaning flips when one word changes.
OUTPUT:  HyperFrames, 1080 x 1920, 30 fps, vertical.
TIME:    76.12 s x 30 = 2284 frames. Narrated (Fish Audio "Documentary" voice, s2.1-pro-free), voice is the clock.
         Scene starts (s): hook 0 · james 10.26 · paper 19.91 · match 29.32 · weights 39.69 · twist 46.92 ·
         scale 56.69 · end 66.54 (timeline.json is the source of truth).

LOOK:    the reference film's medium: real photographs graded dark and cool, white sans type, ONE warm accent.
         ground: the photograph itself (dog-crosswalk, william-james, paper page); never a flat void.
         home stage (match/weights/twist): the crosswalk photo pushed to 2.2x on the asphalt, exposure -1.4,
           so the ground is real texture at ~12% luminance.
         ink: #F4F1EA (warm white) for sentence words; dim words rgba(244,241,234,0.38).
         accent: amber #F2A541 — only on "it", the threads, the winning share. Nothing else is amber.
         sentence: Inter 900, 92 px, tracking -1%, line-height 1.42, 4 lines, centred block, x 90–990.
         captions: Inter 700, 44 px, centred, y = 1250 px baseline band; unread words 45% white, read words 100%.
         labels (query / key / value / %): IBM Plex Mono 500, 30 px, amber or 60% white, with 2 px leader lines.
         credit lines: Inter 400, 22 px, 55% white, bottom-left at y 1330, like the reference.
         vignette 0.35 on photos (media-treatment), no grain, no glow, no blur on type after it lands.
OBJECTS: the dog on the crosswalk (the animal and the street, both literally in frame);
         William James's 1903 portrait; page 1 of arXiv 1706.03762v1 (real title, real abstract line
         "based solely on attention mechanisms"); threads = 1 px–14 px amber Bezier arcs between word centres,
         their width and opacity are the attention weight.
MOTION:  enter expo.out 0.5–0.7 s; camera power2.inOut 2–6 s; exits power3.in 0.25 s; words stagger 0.07 s;
         threads draw with stroke-dashoffset 0.45 s power3.out; numbers count over 0.6 s.
SHOTS:
  hook   0–10.26   crosswalk photo, slow push 1.0→1.12 to the dog's head. The sentence prints word-by-word on the
                   voice (0.54–3.18), "it" turns amber at 5.58, an amber thread arcs it→animal at 6.3. At 7.1
                   ("For a machine") the words become numbered token boxes (1–13). Cut: dip.
  james  10.26–19.91 portrait, push 1.0→1.15 into the eyes over the whole scene. Quote prints at 4.38–6.25
                   in two lines top third. At 7.45 ("nobody knew") the quote drops to 35%. Credit line. Cut: blur swap.
  paper  19.91–29.32 white page fills width; amber highlight sweeps "based solely on attention mechanisms" at 3.68;
                   at 5.0 camera travels up to the title and pushes to 2.4x; at 7.52 amber underline under the
                   title. Exit: zoom through the title (power3.in) into the stage.
  match  29.32–39.69 stage; sentence lands 0.3. 2.71 "it" amber + "query" label. 4.78–6.27 a short "key" tick
                   appears under each other word, staggered 0.06 s. 7.3–9.24 threads draw from "it" to all 10
                   words, widths by weight (animal thickest).
  weights 39.69–46.92 same stage. 0.6 percentages appear over each word. 2.6 the 100% bar builds at y 330:
                   animal 55 · street 15 · rest 30. 4.3 a dot travels along the animal thread into "it",
                   "value" label, "it" underlined with "≈ animal".
  twist  46.92–56.69 same stage. 1.1 "tired." boxed. 2.42 slot roll tired→wide. 3.6 threads swing: animal 55→14,
                   street 15→52, bar re-splits. 6.0 two short readings stacked at y 1080: "tired → it = animal",
                   "wide → it = street".
  scale  56.69–66.54 0.5 every word threads to every word (full 11x11 mesh, 30% opacity). 4.35 camera pulls out:
                   the sentence shrinks into the top-left cell of a 1,000 x 1,000 grid; counter "1,000 x 1,000
                   = 1,000,000". 7.35 the grid stacks into receding layers.
  end    66.54–76.12 back on the crosswalk photo, wide; the sentence with one amber thread it→animal; final hold
                   2.6 s.
BANNED:  flat dark void with floating UI; glow/bloom/neon; particles; purple/blue gradients; glass cards;
         pill chips; corner brackets/HUD; everything fading+sliding up; three cards in a row; text that moves while
         read; amber anywhere except it/threads/winning share; captions repeating the hook sentence (hidden 0–3.9 s).
QA:      t=0.2 (thumbnail: photo + first words), 6.4 (thread it→animal), 15 (James + quote), 24 (highlight on
         abstract), 37 (threads by weight), 44 (100% bar), 50.5 (wide rolled), 53 (threads on street),
         61 (grid), 72 (end frame).
