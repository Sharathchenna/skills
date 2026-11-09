# How attention works in AI — three storylines

Reference: Video-37742.mp4 (Google TrueTime / Einstein). Its shape: a real-world puzzle → a famous
person who hit the same problem → the mechanism shown on one worked example → back to the real
system with real numbers → one line. One recurring object (clocks) carries every scene.

Facts used (all sourced):
- "The animal didn't cross the street because it was too tired / wide" — Google AI blog,
  "Transformer: A Novel Neural Network Architecture for Language Understanding", Aug 2017.
- "Attention Is All You Need", Vaswani et al., Google, 2017: 8 attention heads, d_k = 64,
  score = softmax(Q·Kᵀ / √d_k) · V.
- William James, The Principles of Psychology, 1890: "Everyone knows what attention is."
- Every token scores every token: n tokens → n² scores per head per layer (1,000 → 1,000,000).
- Attention weights shown on screen are illustrative unless taken from a real model run.

---

## A. "Which *it*?"  (RECOMMENDED — one sentence carries the whole film, like the clocks did)

Device: the worked example. Form: one frame that rebuilds — the sentence never leaves the screen;
threads of light between words are the recurring motif.

The viewer reads a simple sentence, gets stuck on one word, and watches the machine solve it — then
change one word and watch every thread re-route. They leave knowing attention = each word asking
every other word "are you the one I need?"

- First 2 s: the sentence fills the frame in white type on a dark street-at-night photo; the word
  **it** turns amber and a question mark pulses beside it. Caption: "What does *it* mean here?"
- Beats: hook (which "it"?) → you solved it instantly → William James, 1890, archive portrait:
  "Everyone knows what attention is" → for a machine, nobody knew how → 2017, Google's paper
  (title page) → "it" sends out a question (query), every word holds up a label (key) → threads
  light by match strength, scores become percentages that sum to 100% → "it" absorbs mostly
  "animal" → swap "tired" → "wide": threads swing to "street" → both readings right, context
  decides → now every word does this to every word, at once, 8 times over → 1,000 words =
  1,000,000 scores per layer → end line.
- Look: photographic night street (the sentence's world) graded cool, warm amber thread light as the
  only accent; IBM Plex Sans captions with word highlight, like the reference.
- Sound: Kokoro narration, low ambient pad, soft tick on each thread connecting.

## B. "The cocktail party"

Device: a moment in someone's day. Form: match cuts — a crowded room becomes a sentence.

A noisy party; across the room someone says your name and you hear it through everything (Colin
Cherry named this the cocktail-party effect in 1953). Each guest becomes a word; your ear becomes
the query; the voices you tune into get louder in proportion to how well they match.

- First 2 s: a blurred crowd photo, a wall of overlapping caption fragments; one word — a name —
  snaps sharp and amber.
- Beats: party noise → your name cuts through → Cherry, 1953 → a transformer has the same problem
  with every word → guests become tokens, volume knobs become attention weights → one sentence
  worked through → many listeners at once (heads) → end line.
- Look: warm photographic interior, shallow focus, amber accent on whatever is "heard".
- Sound: party walla that ducks as attention focuses — the mix itself demonstrates attention.

## C. "Inside one word"  (the bold one)

Device: the object is the explanation. Form: an endless zoom.

The camera dives into the single word "it" — it becomes a row of 512 numbers, the numbers split into
three (query, key, value), the camera flies out along a beam to "animal", through the dot product,
through the softmax, and out the other side as a changed word. Ends pulled back on the whole sentence
glowing with threads.

- First 2 s: extreme close-up of the letters "it" made of tiny digits; pull back reveals the sentence.
- Beats: zoom into "it" → 512 numbers → split into Q / K / V → fly along a beam → multiply, sum,
  squash → land back in "it", now changed → pull back to every word doing it → end line.
- Look: code-built 3D, graphite and amber, no photographs except one archive frame of the 2017 paper.
- Sound: rising synth tone that resolves on each landing.
