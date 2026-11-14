# The fact ledger

Every number, date, name, superlative or claim in the voice **or drawn on screen** points to a record in the
ledger. `scripts/check_facts.py` blocks the build when one doesn't. The design is adapted from
[shorts-kit](https://github.com/howznguyen/shorts-kit) (MIT) and
[paper2video](https://github.com/SunandBean/paper2video) (MIT), with two additions for us: an `illustrative` status
and `asOf` dates for news.

## Files (in the video project)

```
facts/FACTS.json     # array of fact records
facts/SOURCES.json   # array of source records (articles, papers, and every asset: images, music, sounds, fonts)
sources/<n>.md       # saved text of each source you read (for number checks), with URL + retrieval time
SCRIPT.json          # scenes cite fact ids
```

**Fact record**

```json
{"id": "f-0003", "claim": "The Transformer paper was first posted to arXiv on 12 June 2017.",
 "value": "2017-06-12", "quote": "Submitted on 12 Jun 2017", "location": "arXiv abs page",
 "status": "verified", "sources": ["s-0002"], "checkedAt": "2026-11-14"}
```

| Field | Notes |
| --- | --- |
| `id` | `f-0001`… never changes once cited |
| `claim` | one sentence that stands alone |
| `value`, `quote`, `location` | the number as a string; the verbatim text it came from; where (table, paragraph, figure) |
| `status` | `verified` (you opened the source and read the value there) · `contested` (sources disagree; needs `caveat`) · `unverified` (blocks the build) · `illustrative` (made-up example numbers; needs an on-screen "illustrative" tag) |
| `sources` | source ids; required for `verified` |
| `checkedAt` | `YYYY-MM-DD` |
| `asOf` | for news and present-tense claims ("costs $2 per million tokens"); warns when older than 7 days |
| `who_measured` | `vendor` · `independent` · `authors`. Benchmarks must say who ran them, on screen or aloud |
| `mustPreempt` | an alternative number people will quote; goes into the post text |

**Source record**

```json
{"id": "s-0002", "title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762",
 "publisher": "arXiv (Vaswani et al.)", "accessed": "2026-11-14", "tier": 1, "kind": "paper",
 "licence": "arXiv non-exclusive", "saved": "sources/02.md"}
```

- `tier`: 1 = the body that produced the fact (lab, paper, standard); 2 = reference work; 3 = press. A fact whose
  best source is tier 3 gets a warning.
- `role: "candidate-finder"` marks listicles, newsletters, AI digests, Reddit and HN. They can lead you to a
  fact but can't back one.
- Asset kinds (`image`, `footage`, `music`, `sfx`, `font`, `screenshot`, `voice`) need `licence` and, for CC BY,
  a verbatim `attribution`. The pinned comment is generated from these.

## SCRIPT.json

```json
{"mode": "news",
 "scenes": [
  {"id": "hook", "text": "…", "facts": ["f-0001"], "onscreen": ["71.2%", "SWE-bench Verified"]},
  {"id": "end",  "text": "…"}
 ]}
```

A plain array of scenes also works. `onscreen` lists strings drawn on screen in that scene, so their numbers get
checked too. `end`/`share` scenes need no facts.

## Rules

1. **Primary source first.** The lab's post, the paper, the model card, the docs, the standard. Media and
   aggregators are leads.
2. **Read the whole primary**, not the feed summary. Save its text to `sources/<n>.md` with URL and retrieval time.
3. **Two independent sources** for any claim the primary doesn't make itself ("first open model to…", "beats X").
   Two feeds of one outlet, or five articles quoting one tweet, count as one.
4. **Numbers match the source** within rounding, and rounding never improves a result ("71.2" may become "about
   71", never "over 75"). Name the benchmark, the comparison, and who measured it.
5. **The agent never promotes its own research to `verified` without opening the page.** Writing a claim from
   memory is `unverified` until checked.
6. **Independent review.** Before TTS, a fresh subagent that didn't write the script gets only `SCRIPT.json`,
   `facts/` and `sources/` and checks facts, attribution, numbers, framing (no overclaiming, no misleading
   juxtaposition), rumour labels and copyright. Its verdict goes to `review/claims-review.json` with the SHA-256 of
   `SCRIPT.json`. Any script edit makes it stale.
7. **Update check before render** (news): re-fetch the primary; if it changed, recheck the affected facts.

## Commands

```bash
python3 -I tools/check_facts.py --project .            # errors block; warnings name the rule
python3 -I tools/check_facts.py --project . --credits out/   # pinned-comment.txt + caption-draft.txt
```
