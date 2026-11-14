# TikTok and Instagram Reels: the frame, the cover, the post

Rules for publishing a 1080×1920 short on TikTok and Reels. The numbers come from
[shorts-kit](https://github.com/howznguyen/shorts-kit) (MIT), measured from iOS screenshots. Check them again
whenever an app changes its layout. YouTube Shorts fits inside these numbers too.

## Safe zones and layout zones (the hard part)

The gate is `npx hyperframes check`, which warns when DOM text leaves these clear bands (its built-in numbers,
scaled to 1080×1920):

| Platform | Clear band |
| --- | --- |
| TikTok | y 240–840: x 120–960 · y 840–1260: x 120–780 (the like/comment/share rail) |
| Instagram Reels | y 269–1248, x 65–1015 |
| YouTube Shorts | y 288–1248, x 48–888 |

Lay every film out in four zones that sit inside all of them:

| Zone | y | x | What goes there |
| --- | --- | --- | --- |
| Header | 288–480 | 120–888 | the hook title, the equation, the one line of on-frame data. One block at a time |
| Stage | 480–1010 | 130–770 (130–888 above y 840) | the hero object and its DOM labels (`placeLabels` clamps them here) |
| Captions | 1040–1248 | centred, max width 660 | captions only |
| Below 1248 | — | — | nothing anyone must read (platform UI covers it); the "illustrative" footnote at most |

- Earlier versions of this file used shorts-kit's iOS measurements (text to y 1726, rail at x 927). HyperFrames'
  bands are stricter and automated, so they win.
- The 3D world, photos and backgrounds may fill the whole frame. Only **text** must stay in its zone.
- Size things for their final scale: a block that a camera push scales ×1.1 grows past its zone.
- Check with `npx hyperframes check --json --samples 40` (overlaps, safe zones, contrast) and look at
  `check_film.py --sheet` (draws the zones over a contact sheet). Delete old stills after a fix.

## Frame 0 and the cover are different jobs

- **Frame 0** is what the feed autoplays. It must already read: the hook line (≤ 6 words) at y ≥ 300, and the hero
  object on screen. Never black, never a fade in from black.
- **The cover is its own image** (a separate `cover.html` composition rendered to PNG, or a snapshot of a held
  cover state). A frozen frame with half a caption looks like a glitch.
- **The profile grid crops 9:16 to about 1080×1393**, showing only **y 263–1657**. Keep all cover text inside that
  band and leave the bottom-left free for the view count.
- At about 200 px wide in the grid, only one number and about three words survive. Test it:
  `ffmpeg -i cover.png -vf "crop=iw:iw*1.29,scale=200:-1,scale=400:-1:flags=neighbor" thumbtest.png`, then look.
- Cover content: one large, surprising number or object, 2–3 words next to it, and one short curiosity line in the
  accent colour. No spoiler, no logo, no channel name.
- **Cover text must be true on its own.** Shortening a verified sentence can drop a "not entirely" or an "up to".
  Read the cover aloud and ask "meaning what?". Cover claims are in the fact ledger like any other.

## The post text

Write one text for both apps (`check_facts.py --credits` drafts it):

1. **First line: a claim people could argue with, ≤ 100 characters.** It's the only line before "more". No greeting.
2. **Two lines:** the mechanism (why), and the evidence (a date and a number).
3. **Sources:** the primary URL first.
4. **Disclosure:** "Narration is AI-generated." Turn on the app's AI-content label (TikTok "AI-generated", Instagram
   "AI info"). Never clone a real person's voice.
5. **3–5 hashtags.** Don't use strong words ("insane", "game-changer") in the title, cover or hashtags.

**Pinned comment:** verbatim attributions for every CC BY image, sound and track ("modified: cropped, animated"),
and one fact that didn't fit. Post it when you publish. `check_facts.py --credits` builds it from `SOURCES.json` by
id, so nothing gets retyped.

**Get ahead of the argument.** If the vendor's number and an independent number differ, say both in the post
text. If you say it first, it shows care. If you leave it out, it becomes the top comment.

## Audio and encode

| Item | Target |
| --- | --- |
| Integrated loudness | −14 LUFS (±1). −13 is fine; pick one and keep it across the series |
| True peak | ≤ −1 dBTP **measured on the encoded MP4** (AAC adds 0.2–0.6 dB) |
| Voice above music | P90 − P10 of 200 ms RMS windows ≥ 9 dB (checked by `check_film.py`) |
| Music bed level | set per track from the loudness of the part that plays, not a fixed 0.16 |
| Ending | fade the bed to 0 over the last ~6–9 s, then hold the last picture 3–4 s |
| Sound effects | ≤ 5, each normalised to about −20 LUFS, each tied to a visible action at a word |
| Encode | H.264 yuv420p, 30 fps, AAC 48 kHz stereo, faststart |

## Uploading by hand

- Upload from desktop web where possible, with the cover set explicitly.
- Publish public directly. Deleting and re-uploading the same file gets treated as a duplicate and suppressed.
- TikTok doesn't autosave drafts.
- A video that gets zero views often was never shown in the For You feed at all. Check its traffic-source split
  before blaming the hook.

## After posting: learn from the retention graph

| What the graph shows | Fix next time |
| --- | --- |
| Cliff at 0–3 s | The hook or frame 0 failed: change the hook type |
| Dip around 8–15 s | The stakes beat is slow: shorten it or move the "naive way breaks" moment earlier |
| Dip just before the twist | The mechanism dragged: cut a step or add a "predict" pause |
| Rewatch spike | That device worked: reuse it |

Keep a `SERIES-LEDGER.md` line per video: hook type, 3 s retention, average % viewed, where people left, and what
you'll change.
