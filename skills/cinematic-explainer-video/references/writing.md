# Writing the script

These rules apply to both modes. `scripts/check_facts.py` enforces the mechanical ones, and its thresholds live in
`scripts/thresholds.json` with the reason for each. Many of the rules are adapted from
[shorts-kit](https://github.com/howznguyen/shorts-kit) (MIT). Its numbers were measured on a Vietnamese channel,
so treat them as starting values and measure your own.

## Order of work

**Facts → story shape → script → voice → storyboard → scenes.** Don't write a sentence before its fact is in
`facts/FACTS.json` (see `facts.md`). Don't script around an image you can't license.

## The hook (first 3 seconds)

- **A concrete number or image plus a question, inside 3 s.** No greeting, no "in this video", no "did you know".
- **The hook asks and doesn't answer.** Hold the main answer until the evidence is on screen. One draft answered in
  its first 20 s, and the next five scenes explained something the viewer already knew.
- **Name the viewer's assumption, then break it.** "You think X. Actually Y." is stronger than an empty question.
- **Frame 0 is already moving** and shows the subject wide or close, never in a medium shot.
- **For news: the event, a spoken day, and exactly one number.** "On Tuesday, OpenAI…", never "Recently…".
- **The hook rhymes with the peak.** Frame 0 previews the key moment, and the key moment pays it off. Don't promise
  what the peak doesn't show.
- Write **three hooks** of different types (see `cs-concepts.md` for the list) and pick one. Record why the others
  lost in `STORYLINES.md`.

## Length and pace

- 45–90 s. Plan at **2.5–3 words per second**. Fish "Documentary" at speed 0.9 reads about 3 w/s, so 60 s ≈ 150
  words, 90 s ≈ 220 including holds. Measure your own voice once and write the number down.
- **About one new piece of information every 2.5 s.** A scene over ~20 s means moving details (years, sample sizes,
  source names) onto the frame and keeping only the mechanism in the voice.
- **Anything to be read gets time:** one image with one idea ≥ 5 s, a comparison ≥ 8 s, a table or timeline ≥ 6 s.
  Add declared silence after the line; don't stretch shots by hand.
- Change only one speed control. Speed settings don't carry over between TTS engines.

## Sentences for a TTS voice (they become the captions too)

- **Full stops make pauses. Commas, colons and dashes mostly don't.** End the sentence where a listener needs to
  breathe. Test this once on your TTS voice.
- **No `:` `—` `–` ` - ` or "etc." in spoken text.** They show on screen in the captions and make the voice read like
  an outline. (Colons between digits are fine.)
- **≤ 25 words per sentence.** Count a spoken number as one word. Avoid a run of clipped 3–5 word sentences; that
  reads as a summary, not an expert.
- **Each scene opens with a name, not a pronoun** (it, this, that, they). The viewer may have just scrolled in.
- **No riddle sentences, no moral endings, no three sentences in a row starting with the same word.**
- **Banned phrases** (full list in `thresholds.json`): "let's dive in", "deep dive", "did you know", "you won't
  believe", "it turns out", "here's the thing", "mind-blowing", "game-changer", "groundbreaking", "revolutionize",
  "changes everything", "delve", "in a world where", "buckle up", "stay tuned", "unlock", "link in bio". At most one
  intensifier per video (really, truly, extremely, literally). AI news is where these creep in.
- **Define every term aloud in one plain sentence, or don't use it.** A proper noun says what it is at first
  mention ("Anthropic, the company behind Claude").
- **Every number gets a picture.** "Out of every hundred, about thirty-eight…". Say numbers the way people say them;
  write the display form on screen ("9 m" on screen, "nine metres" in the voice).
- **Contrasts need both sides named earlier, and the contrast itself must be a fact in the ledger.** A neat
  "A did X, but B did Y" can invent a relation between two true facts.
- **Sources go on the frame, not in the voice.** Exception: when the document is a character (the paper reveal).
- **Tension check before TTS:** does each scene's last sentence pull the viewer on? Does the payoff add something
  new, never a recap? Is there one human moment (a person, place, time) told slower? Build with a long sentence,
  then hit with a short one.

## TTS hygiene

- Pin voice, model and speed in `SCRIPT.json`'s project notes. Cache on a hash of text + settings.
- After `build_timeline.py`, read its warnings: it flags **TTS loops** (a 1–3 word phrase repeated 3+ times in a
  row) and transcript words that differ from the script. Fix a loop by rewriting the line, not by re-rolling.
- Keep two maps: `pronounce` (spoken respellings, e.g. "GPT" → "G P T") and `display` (caption forms).

## Story shapes ("flows")

All shapes share one skeleton: **hook → body beats → payoff (one new thing, never a recap) → 3–4 s hold.** Pick by
the shape of the fact, not by habit. Write at least two candidate shapes in `STORYLINES.md` and record why the loser
lost.

| Shape | Use when | Beats | Trap |
| --- | --- | --- | --- |
| **Explain it** (CS default) | the value is understanding a mechanism | hook, problem, naive way breaks, mechanism on one example, twist (failure mode), scale, payoff | sliding into a lecture; each scene must answer the question the last one raised |
| **News explainer** (AI news default) | this week's event with a "why" you can show | hook, what happened, why it matters, how it works (1 picture), proof, caveat, payoff | listing five causes; publishing more than 7 days late |
| **The picture lies** | the chart or the wording contradicts the measurement (launch-day benchmark charts) | hook, the picture, the number, the gap, payoff | drawing your own line before the data |
| **Trace back** | a viral claim with a citation chain ("AI passed the bar exam") | hook, origin, link 1–3, payoff | a link with no real document on screen |
| **Side by side** | model A vs B, or human vs model, on ONE decisive measurement | hook, thing 1, thing 2, ruler, payoff | not true to scale; one side only |
| **Record changed** | a benchmark "beaten" because the definition changed | hook, record, change, mechanism, unchanged, payoff | calling the old value wrong |
| **One journey** | the subject travels (a packet, a request, a key through a hash table) | hook, leg 1–3, destination, payoff | no visible destination early |
| **One small moment, then pull out** | a famous bug or incident (Ariane 5, Therac-25, a leap second) | hook, before, moment, aftermath, consequence, payoff | showing the scale before the moment |
| **Old story, new face** | concepts named after stories (Byzantine generals, dining philosophers) | hook, myth, mapping, evidence, payoff | forcing the mapping |
| **Reading a graph** | the idea is a place on ONE chart (Big-O, Moore's law) | hook, character, curve, points, payoff | a static chart for half the video; a sketch shown as data |

"Explain it" deliberately has no belief reversal. Our "twist" (change one input and watch the mechanism re-route)
is a demonstration, so it fits.

## Visual truth

- **Say it = show it.** Anything the narration names appears on screen within ±1.5 s, as it's said. Graphics are
  drawn onto the subject, not floated as cards.
- **On-frame text never repeats the caption.** It carries what the ear can't catch: units, decimals, names, years.
  Use it in at most half the scenes; headlines ≤ 6 words.
- **Scale is honest.** Bars start at zero; comparisons are true to scale or labelled "not to scale".
- **Admit the drawing lies.** When a visual simplifies, a small grey line says so ("illustrative weights",
  "real filters: millions of bits"). Every non-footage shot is our illustration, not evidence.
- **No fake headlines, UIs, documents or AI images standing in for real things.** Real evidence (screenshots,
  paper pages) appears as a document *inside* our world, with a credit line.
