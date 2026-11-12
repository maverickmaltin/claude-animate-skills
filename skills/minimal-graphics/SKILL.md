---
name: minimal-graphics
description: Explains any idea with simple shapes, moving dots and clean animation, as a 1080x1920 MP4. Use for /minimal-graphics with an idea or question, or any ask for a minimal explainer animation.
license: MIT
---

# /minimal-graphics: an idea explained with shapes and moving dots

The user gives an idea ("how an idea goes viral", "how a bill becomes a law", "the water cycle", "where your attention
goes"). You pick the motion pattern that shows it, write a small spec, check a frame, render the video and hand back a
silent MP4 (5-7 seconds).

`${CLAUDE_SKILL_DIR}` below is this skill's folder (the one this SKILL.md is in). If your environment doesn't fill it in,
use that folder's path. Save everything in the user's current folder, or the folder they name.

## 0. Setup check

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" --check
```

It takes a few seconds; run it if you're not sure this computer has been set up. `"ready": true` means go. Otherwise run
the commands it lists under `"fix"`, telling the user it's a one-time install: `python3 -m pip install playwright` (the
browser driver), `python3 -m playwright install chromium` (only when Google Chrome or Edge isn't installed, about 150 MB)
and `python3 -m pip install imageio-ffmpeg` (only when ffmpeg is missing). If pip refuses with "externally managed
environment", make a private environment once and use its Python for every command:
`python3 -m venv ~/.animate-skills && ~/.animate-skills/bin/pip install playwright imageio-ffmpeg`, then
`~/.animate-skills/bin/python -m playwright install chromium` if needed. On Windows, use `py` instead of `python3`.
No browser possible here (for example the Claude app's sandbox)? See the end of this file.

## 1. Pick the pattern

| Pattern | Shows | Good for | Fields |
|---|---|---|---|
| `spread` | One dot reaches 2-4 others, each of those reaches more, ring by ring | Viral ideas, word of mouth, chain reactions, referrals, things that double | `branches` (2-4, default 3), `depth` (2-5, default 4), `sequence` (optional short labels per ring, e.g. `["1","3","9","27","81"]` or `["$1k","$2k","$4k"]`, shown in a line under the title as each ring lights; a few characters each) |
| `flow` | Numbered shapes in order, a dot travelling from each to the next, then a steady stream | How something works, a process, a pipeline, a recipe | `steps`: 2-6 short labels; `shapes` (the shapes are decoration: `["circle"]` makes them all circles) |
| `cycle` | Steps on a loop with a dot that keeps orbiting | Water cycle, habit loop, feedback loops, seasons, sleep cycles | `steps`: 3-6 short labels; `center`: a word in the middle |
| `converge` | Many dots flowing into one circle that grows (or `"direction": "out"`: one circle sending dots out to several) | Where your attention, time or money goes; many inputs into one result | `sources`: 2-6 labels (optional); `weights`: how many dots each gets; `center`: the word in the circle; `count`: dots (default ~40) |
| `compare` | Two or three amounts side by side, as dots (one per unit) or as circles sized by the amount | "X vs Y" amounts: sugar, cost, time, calories | `groups`: `[{"label": "...", "value": n, "unit": "..."}]`; `highlight`: index of the one to colour |

If none fits well, use the closest one and say so in one line; don't force a misleading picture. A pattern shows the
shape of an idea; the `takeaway` line says the point in words. Ideas about two forces balancing (supply and demand,
work-life balance) have no pattern of their own: show the loop that settles them as a `cycle`, or say so.

## 2. Write the spec

Save `minimal-<topic>.json`:

```json
{
  "title": "How an idea goes viral",
  "pattern": "spread",
  "branches": 3,
  "depth": 4,
  "takeaway": "Each person tells three more",
  "theme": "coral"
}
```

Common fields: `title` (the idea as a short headline or question, up to ~40 characters), `subtitle` (optional small line
under the title), `takeaway` (the one-line point; it appears under the title when the animation finishes, and long ones
shrink to fit), `theme` (`coral` default, `ink` black, `paper` off-white, `blue`, `mint`), `size` (`"1080x1920"` default,
`"1080x1080"`, `"1920x1080"`), `duration` (seconds; default 5-6, more with a takeaway; a longer one only holds the end
longer), `speed` (0.7 = everything 30% slower, 1.3 = faster), `fps` (default 30).

Writing rules:
- Labels are tiny: up to 4 words each (sequence labels: a few characters). No jargon.
- Numbers must be true. If the idea needs figures you're not sure of, leave them out or say they're illustrative.
- One idea per video. If the user's idea has two parts, make two videos (two specs).

Examples in `examples/`: `idea-goes-viral.json`, `bill-becomes-law.json` (flow), `water-cycle.json` (cycle),
`where-attention-goes.json` (converge), `soda-vs-apple.json` (compare).

## 3. Check two frames

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" minimal-<topic>.json --still 2 --out minimal-<topic>-check1.png
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" minimal-<topic>.json --still end --out minimal-<topic>-check2.png
```

`--still` takes seconds, or `end`. Look at them: labels readable and not clipped, the picture says the idea? Adjust and
check again if not.

## 4. Render the video

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" minimal-<topic>.json --out minimal-<topic>.mp4
```

About 10-25 seconds. Delete the check images.

## 5. Deliver

Give the user the MP4's path (show it if your environment can display files). It has no sound, ready for music or a
voiceover. Offer one variation (another pattern or theme).

## No browser here? (for example the Claude app's sandbox)

If the setup check can't get a browser running, write the animation as a page instead:
`python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" minimal-<topic>.json --html minimal-<topic>.html`. The page plays in any
browser (show it as an artifact if you can). Tell the user the MP4 needs Claude Code on a computer, or a screen recording
of the page.
