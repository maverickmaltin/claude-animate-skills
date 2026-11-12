---
name: graph
description: Turns your numbers into an animated chart video that builds itself on screen (1080x1920 MP4). Use for /graph with numbers, a table or a CSV, or any ask to animate a chart.
license: MIT
---

# /graph: your numbers become an animated chart

The user gives numbers in any shape: `Mar 200K, Apr 650K, Nov 1.5M`, a pasted table, a CSV file, a screenshot, or a
sentence. You turn them into a small spec, check a frame, render the video and hand back a silent MP4 (about 5 seconds).

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

## 1. Write the spec

Save `graph-<topic>.json`:

```json
{
  "title": "My Instagram followers",
  "subtitle": "2026",
  "data": [["Mar", 200000], ["Apr", 650000], ["Nov", 1500000]],
  "source": "Instagram",
  "theme": "night"
}
```

Rules:
- Use the user's exact numbers. Never invent, smooth, round or fill in values. If something is really ambiguous (which
  column, what unit), ask one short question; otherwise go.
- Write full numbers: 650K → `650000`, 1.5M → `1500000`, 12% → `12` with `"suffix": "%"`.
- Keep labels short (up to ~8 characters looks best): `Mar`, `Q1`, `2024`, `Mon`.
- The title says what the numbers are, in the user's words where possible (about 30 characters at most; `|` forces a
  line break). Add `subtitle` and `source` only when the user gave them or they're plain from the request ("my Instagram
  followers" → source Instagram); don't make them up.

| Field | What it does |
|---|---|
| `title`, `subtitle` | Headline and a small line under it (period, unit). |
| `data` | `[["label", number], ...]` or `[{"label": "...", "value": n}, ...]`, in order. |
| `type` | Leave out for automatic: bars up to 10 values; a line for longer series, and for values that change little next to their size (a weight going 210 → 178, a price, a temperature), where the line zooms in on the range. `"bar"` or `"line"` to force. |
| `prefix`, `suffix` | Units: `"$"`, `"€"`, `"%"`, `" kg"`. |
| `decimals` | Force decimals. Default: each value keeps its own. |
| `compact` | Default shows 10,000+ as 12K / 1.5M / 2B. `false` for full numbers. |
| `callout` | Leave out for the automatic growth tag from first to last value (`↑ 7.5x`; whole numbers from 10x up, `↑ 77x`; `↑ 32%`; `↓ 18%`). A short text of your own (`"Back in profit"`), or `null` for none. |
| `good` | `"down"` when lower is better (weight lost, debt paid off, costs, race times): a drop gets a green tag instead of a red one. |
| `highlight` | Which bar is gold: `"last"` (default), `"max"`, an index, or `"none"`. |
| `theme` | `night` (dark navy, coral bars; default), `light`, `sunset`, `mint`. |
| `source` | Small "Source: ..." note under the chart. |
| `size` | `"1080x1920"` (vertical, default), `"1080x1080"`, `"1920x1080"`. |
| `duration`, `fps` | Seconds (default ~5) and frames per second (default 30; 60 is smoother but slower). |

Examples: `examples/instagram-followers.json` (bars), `examples/website-visitors-line.json` (a line).

## 2. Check the last frame

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" graph-<topic>.json --still end --out graph-<topic>-check.png
```

Look at the image (2-3 seconds to make): labels readable, nothing overlapping, the numbers exactly the user's. Fix the
spec and check again if not.

## 3. Render the video

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" graph-<topic>.json --out graph-<topic>.mp4
```

About 10-20 seconds. Delete the check image.

## 4. Deliver

Give the user the MP4's path (show it if your environment can display files). It has no sound, ready for music or a
voiceover. Offer one quick variation (another theme, the square size, a line instead of bars).

## No browser here? (for example the Claude app's sandbox)

If the setup check can't get a browser running, write the animation as a page instead:
`python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" graph-<topic>.json --html graph-<topic>.html`. The page plays the
chart in any browser (show it as an artifact if you can). Tell the user the MP4 needs Claude Code on a computer, or a
screen recording of the page.
