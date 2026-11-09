# skills

Agent skills (Claude Code `SKILL.md` format).

| Skill | What it does |
| --- | --- |
| [cinematic-explainer-video](skills/cinematic-explainer-video/SKILL.md) | Vertical narrated 3D explainer shorts: a Three.js world under the whole film, archive photos with parallax, word-highlight captions, no hard cuts — rendered with HyperFrames. Includes reference-video analysis, Fish Audio TTS, timing scripts and a full worked example. |

## Install

Copy a skill folder into your skills directory:

```bash
git clone https://github.com/Sharathchenna/skills
cp -r skills/skills/cinematic-explainer-video ~/.claude/skills/
```

`cinematic-explainer-video` builds on the HyperFrames skills (`npx hyperframes skills update` installs them).
