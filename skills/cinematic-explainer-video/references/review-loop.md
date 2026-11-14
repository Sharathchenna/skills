# Review loop: the builder never grades its own work

Adapted from [motion-video-kit](https://github.com/echris6/motion-video-kit) (MIT), Code2Video's TeachQuiz
(MIT) and [codebase-video](https://github.com/OnurGumus/codebase-video)'s audit briefs. The prompts below are our own.

## The loop

```
PLAN.json / SCRIPT.json + facts/ + quiz.json      → Critic 0: storyboard + claims (fresh subagent)
beat board: world_frames.cjs still per beat        → user approves before voice and overlays
build → automated gates green                      (check_facts.py, hyperframes check, check_film.py)
preview render                                     → Critic 1: full film + quiz (fresh subagent)
fix the top items, largest gap first
re-render                                          → Critic 2: verify (fresh, gets Critic 1's report)
repeat verify until SHIP, at most 3 film critics; then stop and show the user the open items
final render → gates again on the final file → review/approval.json with the MP4's SHA-256
```

- **Each critic is a new subagent** (`Agent`, `subagent_type: general-purpose`), never a fork of the builder. It
  gets no notes about intentions and never sees the builder's `REVIEW.md` or fix list.
- **What the critic gets:** the MP4 path; `brief.md` (audience, the one claim, the hook, 3–5 things the viewer
  should learn, each with its visual); `facts/`; `quiz.json`; the output of the automated checks; `style.md`
  and 2–3 frames of the target look. Verify rounds also get the previous critic's report.
- **The critic extracts its own frames:** a contact sheet every 0.5 s, full-resolution frames at each beat, and
  dense 1/30 s strips ±0.5 s around every seam in `timeline.json`.
- **It returns ≤ 900 words** to `review/critic-<n>.md`: scores, per-beat notes with timestamps, ranked defects,
  the top 6 concrete fixes, and a verdict.

## Rubric (1–5 each)

| | Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- | --- |
| A | Hook (0–3 s) | black, logo or generic question | readable question, subject on screen | a specific gap + the real object on frame 0; motion by 2 s; reads at ¼ size |
| B | Mechanism visible | the voice describes steps the picture doesn't show | most steps shown, some only as text | every step named happens on screen as it's said; one worked example end to end |
| C | Motion = meaning | decorative drifting; busy start then static | mostly operations, some filler | every non-camera motion is an operation; a meaningful change at least every 3 s |
| D | Accuracy | a wrong number or claim | correct but unsourced or unlabelled illustrative values | everything matches the ledger; illustrative values labelled; who-measured stated |
| E | Twist / payoff | none, or unrelated | told, not shown | the failure mode or caveat re-run on the same object; the end answers the hook and returns to frame 1 |
| F | Phone legibility | clipped, overlapping, tiny | readable but cramped or empty | hero fills 60–85% in feature beats; nothing in platform UI zones; text ≥ 36 px |
| G | Continuity & craft | hard cuts, pops, camera inside a wall | a few rough seams | every seam is a camera move, dissolve or zoom-through; no one-frame pops; glow never eats text |
| H | Sound | music fights the voice; random effects | clean, a few unmotivated sounds | clear voice, continuous bed, effects only on visible actions |
| Q | Quiz | ≤ 1/4 | 2/4 | ≥ 3/4 including the key-moment question |

**Pass:**
- All automated gates are green.
- No dimension is below 3.
- Accuracy (D) is 5.
- Hook, mechanism and motion (A, B, C) are each ≥ 4.
- The total is ≥ 32/40.
- The quiz scores ≥ 3/4, with the key-moment question right.

## Quiz (TeachQuiz-lite)

At planning time write `quiz.json`: 4 multiple-choice questions with 4 options each. Ask one about the claim, one
about the key moment ("why can a Bloom filter say *maybe* for a word it never saw?"), one about the twist or caveat,
and one transfer question. The critic answers twice:
1. From the question text alone. It answers INSUFFICIENT where it would need prior knowledge.
2. From the video only (frames + transcript), citing timestamps.

The score is round 2. A question round 1 already answers is a weak question: rewrite it. This is a smoke test. A
language model isn't a viewer, and the real retention graph decides (see `platform.md`).

## Prompts

**Storyboard + claims critic (before voice)**

> You are reviewing the plan for a 60–90 s vertical explainer before anything is recorded. You did not write it.
> Files: SCRIPT.json, PLAN.json (if any), facts/FACTS.json, facts/SOURCES.json, sources/, quiz.json, and
> references/writing.md, facts.md and platform.md from the skill.
> 1. Open every cited source and check each fact's value and wording against it. Report any number, date, name or
>    superlative in the script or `onscreen` strings that isn't backed, is rounded upward, drops a qualifier, or
>    hides who measured it.
> 2. Check framing: overclaiming, misleading contrasts, rumour labels, and anything that would need a correction.
> 3. Check the story: is the claim one sentence? Does the hook ask a specific question that the ending answers? Is
>    the twist the real failure mode or caveat? Does every beat have a picture that adds information? Is any beat
>    filler? Does anything break writing.md?
> Return pass / fix / block for facts, attribution, numbers, framing, rumour labels, copyright and story, with
> concrete line-level fixes. Write it to review/claims-review.json, including the SHA-256 of SCRIPT.json.

**Full-film critic**

> You are the critic for a finished vertical explainer. You did not make it and you have no notes from the maker.
> Inputs: <mp4>, brief.md, facts/, quiz.json, check results, references/style.md and platform.md, and reference
> frames. Extract frames yourself (ffmpeg): a sheet every 0.5 s, full frames at each beat, dense strips around
> seams. Watch as a phone viewer scrolling a feed would.
> Score A–H from the rubric in review-loop.md with one line of evidence each (timestamp + what's on screen). Answer
> the quiz twice as described. List defects ranked by how much they cost the viewer, with timestamps and screen
> positions. Give the top 6 fixes as concrete, buildable changes. Verdict: SHIP or FIX. ≤ 900 words.

**Verify critic**

> You get the previous critic's report and a new render. For each item say FIXED, PARTLY or STILL PRESENT, with
> evidence. Then look for regressions: text over text during crossfades, wrong layering, the camera inside
> geometry, new clipping, timing drift. Verdict: SHIP, or ONE MORE PASS with at most 3 fixes.

## Automated gates (run before any critic)

| Gate | Tool |
| --- | --- |
| Composition errors | `npx hyperframes check --json` (via `check_summary.py`) |
| Ledger, number backing, writing lint | `check_facts.py` |
| Encode, duration, frame 0, black/frozen frames, loudness, voice-over-music spread, safe-zone sheet | `check_film.py` |
| TTS loops, transcript vs script | `build_timeline.py` warnings |
| Determinism | `world_frames.cjs` at the same times twice, in different order; identical PNGs |

Keep `REVIEW.md` for honest notes on what was measured versus only looked at. Verdicts come from the critics.
