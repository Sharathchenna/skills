# Pitfalls hit while building the attention video (and the fix)

| Symptom | Cause | Fix |
| --- | --- | --- |
| The whole 3D world renders black in snapshots, but renders fine alone | An HTML overlay scene's `#root` had an opaque background and covered the world | Overlay scenes above the world: `#root { background: transparent }` |
| An animation lands one word early/late | Word index counted by eye ("a", "the" shift every later index) | `python3 scripts/word_index.py`, then wire anchors by printed index |
| Camera shot turns into a flat blue void | Camera keyframe placed behind the rack wall | Keep camera keys on the hall side; move the wall further out |
| Text glows into mush | Bloom threshold too low; white text ≥ 1.0 | threshold ≈ 0.92, base text brightness 0.9, highlights ×1.5 |
| Wavefront disc covers the whole frame | Pulse scaled in world units without checking camera distance | Max radius ≈ 1.2 at a 7-unit camera distance |
| Bar animation stutters / lint `gsap_non_transform_motion` | Tweening `left`/`width` | Full-width segments, animate `x` + `scaleX` |
| Frame 0 does not show the hidden-state you set | `tl.set(..., 0)` for initial hides | Put initial `opacity: 0` in CSS |
| Thumbnail is empty | Sentence starts at opacity 0 | Start dim (0.3–0.55) so frame 0 already reads; a title line at the top |
| Captions overlap the 3D block | Block too low in frame | Lower the look-at target / pull the camera back; captions in the y 1180–1460 band |
| Captions unreadable over a white document | No backing | Scrim on caption groups only during the page scene |
| Credit lines fail contrast | Small grey text over photos | `data-layout-ignore` + a dark rounded backing |
| Fish Audio HTTP 402 | Paid model without API credit | header `model: s2.1-pro-free` |
| `npx hyperframes transcribe` output "missing" | It writes `transcript.json` next to the input file | Move it to `tmp/tr/<id>.json` after each run (build_timeline.py does) |
| Snapshot batch shows a later state early | Snapshot quirk when several `--at` times are captured in one run | Re-snapshot that time alone before "fixing" it; renders play in order and were correct |
| Running a long snapshot/render blocks the agent | Foreground command | Run renders in the background and wait for completion |
| Title hidden under the Reels top bar and cut from the profile grid | Hook title at `top: 210px` | Titles start at y ≈ 300; cover text inside y 263–1657 |
| A word of every caption line sits under the like button | Caption and quote blocks wider than 774 px (the attention example's quote ran to x 990) | Max width 774 px centred; check with `check_film.py --sheet` |
| Captions show ":" and "—" and the voice runs on | Colons and dashes in narration ("wrote: everyone knows…") | Full stops instead; `check_facts.py` flags them |
| The voice changes pace between scenes | One TTS request per scene | Pin voice, model and speed; listen across seams; re-take a scene that stands out |
| A phrase repeats three times in the voice but every number check passes | TTS loop | `build_timeline.py` loop warning; rewrite the line |
| A fixed bug "still" shows in review | Looking at old stills that weren't regenerated | Delete stills after each fix |
| A truncated MP4 that ffmpeg reported as fine | Piping ffmpeg into `head` | Never pipe ffmpeg output into `head`; read the whole log |
| A number on screen nobody can source | Wrote the line before the fact | Facts first; every scene cites ledger ids (`facts.md`) |
