# skills

Agent skills (Claude Code `SKILL.md` format).

| Skill | What it does |
| --- | --- |
| [cinematic-explainer-video](skills/cinematic-explainer-video/SKILL.md) | Vertical narrated 3D explainer shorts for TikTok and Reels: a Three.js world under the whole film, archive photos with parallax, real screenshots as evidence, word-highlight captions, no hard cuts — rendered with HyperFrames. Two modes: **AI news** (a 30+ source news collector, fact ledger, screenshot capture) and **CS concepts** (planning cards, simulate-then-render, a visual vocabulary for 16 classic ideas, series planning). Includes a fresh-critic review loop, automated fact and film checks, Fish Audio TTS, timing scripts and a full worked example. |

## Install

Copy a skill folder into your skills directory:

```bash
git clone https://github.com/Sharathchenna/skills
cp -r skills/skills/cinematic-explainer-video ~/.claude/skills/
```

`cinematic-explainer-video` builds on the HyperFrames skills (`npx hyperframes skills update` installs them).

## Acknowledgements

Ideas in `cinematic-explainer-video` were adapted, in our own words and code, from these open-source projects:

- [howznguyen/shorts-kit](https://github.com/howznguyen/shorts-kit) (MIT): fact-ledger design, TikTok/Reels safe
  zones, cover-crop rule, TTS writing rules, story-shape taxonomy, audio targets.
- [KoroLiu/auto-news-shorts](https://github.com/KoroLiu/auto-news-shorts) (MIT): news collection, model-version
  dedupe, covered-story dropping, number backing.
- [echris6/motion-video-kit](https://github.com/echris6/motion-video-kit) (MIT): the independent critic loop.
- [showlab/Code2Video](https://github.com/showlab/Code2Video) (MIT): quiz-based evaluation (TeachQuiz).
- [SunandBean/paper2video](https://github.com/SunandBean/paper2video) (MIT): claims file covering on-screen strings.
- [Agent-Field/reels-af](https://github.com/Agent-Field/reels-af) (Apache-2.0) and
  [gauravfs-14/vidxiv](https://github.com/gauravfs-14/vidxiv) (MIT): paper-to-short writing rules and figure crops.
- [HeyChengC/wallstreet-explainer](https://github.com/HeyChengC/wallstreet-explainer) (no licence stated; idea only): screenshot + highlight boxes.
- [BusyBee3333/code-to-reels](https://github.com/BusyBee3333/code-to-reels) (MIT) and
  [arav31/CourseToShortsSkills](https://github.com/arav31/CourseToShortsSkills) (ideas only): the "naive way breaks"
  beat, planning cards, series planning.
- [Raminshiraz/raft-visualizer](https://github.com/Raminshiraz/raft-visualizer) (MIT): simulate, then render the trace.
- [OnurGumus/codebase-video](https://github.com/OnurGumus/codebase-video) (MIT): audit brief structure.
- [runesleo/claude-video-kit](https://github.com/runesleo/claude-video-kit) (MIT): review receipts bound to a file hash.
