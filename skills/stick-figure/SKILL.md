---
name: stick-figure
description: Turns an idea or question into a cartoon explainer acted out by stick figures, pets and props, as a 1080x1920 MP4. Use for /stick-figure or any ask for a stick-figure animation.
license: MIT
---

# /stick-figure: a cartoon explainer with stick figures

The user gives an idea or a question ("why are yawns contagious?", "why do cats knock things off tables?", "why do we
procrastinate?"). You write the answer in one line, stage a tiny scene that shows it, check a few frames, render the video
and hand back a silent MP4 (5-7 seconds).

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

## 1. Plan the scene (briefly)

- **Title**: the question or idea, short (up to ~40 characters).
- **Answer**: the one-line explanation, true and simple (up to ~45 characters). It appears about a second in.
- **The scene**: 1-4 characters acting out the answer in 3-8 beats over 5-7 seconds. Show it happening: yawns spreading
  from person to person, a cat pushing a mug off the table, a dog waking up and wagging. The last beat is the payoff and
  stays on screen to the end.

## 2. Write the spec

Save `stick-<topic>.json`. Example (`examples/knock-things-off.json`):

```json
{
  "title": "Why do cats knock things off tables?",
  "answer": "Hunting instinct, and it gets your attention",
  "scene": "room",
  "props": [{"type": "table", "x": 0.62}, {"type": "cup", "x": 0.70, "on": "table", "wobbleAt": 1.6, "fallAt": 2.15},
            {"type": "plant", "x": 0.08}],
  "figures": [{"id": "cat", "kind": "cat", "x": 0.52, "on": "table", "head": "#F4A261", "hatColor": "#F4A261"},
              {"id": "you", "x": 1.2, "label": "You", "hat": "hair", "hatColor": "#6B4423"}],
  "beats": [
    {"who": "cat", "do": "look", "at": 0.0, "for": 1.0, "to": 0.7},
    {"who": "cat", "do": "swipe", "at": 1.0, "for": 1.2, "to": 0.7, "say": "Boop"},
    {"who": "you", "do": "run", "at": 2.3, "for": 0.8, "to": 0.86},
    {"who": "you", "do": "surprised", "at": 3.1, "for": 0.9, "say": "My mug!"},
    {"who": "cat", "do": "sit", "at": 3.3, "for": 1.0},
    {"who": "you", "do": "point", "at": 4.1, "for": 1.2, "to": "cat"},
    {"who": "cat", "do": "love", "at": 4.4, "for": 1.0}
  ],
  "arrows": [{"from": "cat", "to": "you", "at": 3.6, "for": 0.4}]
}
```

More: `examples/contagious-yawns.json` (three people), `examples/procrastination.json` (an office, someone walking in),
`examples/dog-wags.json` (a dog and a kid in a park).

**Scene**: `street` (sky, pavement, road), `park` (sun, hills, grass), `room`, `office` (window with a city), `classroom`
(add `"board": "text"` for the chalkboard), `night` (stars and moon), `plain` (add `"background": "#hex"`).

**Figures** (up to 5; `x` from 0 = left edge to 1 = right edge; keep people 0.12-0.88 and ~0.3 apart; use -0.2 or 1.2 to
start off-screen and walk in):
- `kind`: `person` (default), `cat`, `dog` (side-on, about a third of a person's height).
- `id`, `x`, `label` (a name under their feet: "You", "Your brain"), `scale` (0.6-0.8 for a child), `facing`
  (`left`/`right`; otherwise they face the middle, then wherever they last moved, pointed or swiped).
- `on`: stand on furniture: `table`, `desk`, `bench`, `shelf`, `bed` (put the furniture prop at the same x).
- People: `hat` (`cap`, `tophat`, `beanie`, `crown`, `bow`, `hair`), `hatColor` (also the hair colour), `head` (face
  colour), `glasses` (true), `tie` (a colour). Pets: `head` (fur colour), `hatColor` (ear colour).

**Beats** (`{"who", "do", "at", "for", "to", "say"}`, in seconds): `to` is another figure's id or an x (0-1).

| `do` (people) | What it looks like | `do` (people) | What it looks like |
|---|---|---|---|
| `walk`, `run` | Moves to `to` | `talk` | Mouth moving, one hand gesturing |
| `wave` | Waves, big smile | `yawn` | Arms up, big yawn, eyes shut |
| `look` | Turns its head to `to` | `point` | Points at `to` (a figure's head, or table height at an x) |
| `think` | Hand on chin (with `say`: a thought bubble) | `shrug` | "Who knows?" |
| `jump` | Jumps for joy | `cheer` | Arms up in a V |
| `surprised` | Jumps back, "!" | `sad` | Head down, a tear |
| `sleep` | Eyes shut, Zzz | `laugh` | Bouncing, big grin |
| `dance` | Dancing, music note | `idea` | Arm up, light bulb |
| `love` | Heart | `fall` | Falls over and stays down |

Pets: `walk`, `run`, `jump`, `sit`, `swipe` (a paw swipe toward `to`, for knocking things over), `sleep` (curled up, Zzz),
`meow`/`bark`/`talk` (mouth open; add `say`), `surprised` (arched back, "!"), `look` (turns to face `to`), `wag` (happy,
tail going), `love`, `idea`, `sad`.

`say` puts a speech bubble over that figure for that beat (up to 5 words; `think` makes a thought bubble; the bubble
replaces the beat's little icon). Each figure's **last beat holds its pose to the end** (except walking, running, talking
and yawning), so end on the payoff.

**Props** (`{"type", "x", ...}`): furniture and set pieces `bus-stop`, `tree`, `bench`, `desk` (with a laptop), `table`,
`door`, `sign` (with `text`), `car` (`"drive": 1` drives it past), `house`, `plant`, `lamp`, `tv`, `bed`; and small
objects `cup`, `mug`, `glass`, `vase`, `bottle`, `plate`, `ball`, `book`, `phone`, `box`. Small objects sit on the floor or
`"on": "table"` (or `desk`, `bench`, `shelf`, `bed`; give them an x inside that furniture's width, which is about ±0.15
around its x); `"wobbleAt": s` makes one wobble, `"fallAt": s` knocks it off (`"fallDir": -1` to the left); cups,
glasses, vases, bottles and plates smash with a CRASH (`"sound": "SMASH!"` changes the word), balls bounce away.
Also `color`, `scale`, `front: true` (drawn in front of the characters).

**Arrows** (`{"from", "to", "at", "for", "color", "hold"}`): a dotted arrow from one head to another, like "it passes on";
`hold` is how long it stays after drawing (default 0.9 s).

Other fields: `answerAt` (seconds; default ~1.1), `size` (`"1080x1920"` default, `"1080x1080"`, `"1920x1080"`),
`duration` (default: the last beat's end + 1.3 s, at least 5), `fps` (default 30).

Staging tips: start a beat at 0.0 so nobody is frozen at the start; overlap beats a little so something always moves;
each beat 0.8-1.6 s; put the knock-over or the key moment in the middle and the reaction after it.

## 3. Check three frames

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" stick-<topic>.json --still 0.5 --out stick-<topic>-check1.png
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" stick-<topic>.json --still 2.5 --out stick-<topic>-check2.png
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" stick-<topic>.json --still end --out stick-<topic>-check3.png
```

`--still` takes seconds, or `end`. Look at them: characters on screen and facing the right way, bubbles not covering
faces or the title, the story readable without sound. Adjust positions or timing and check again if not.

## 4. Render the video

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" stick-<topic>.json --out stick-<topic>.mp4
```

About 15-25 seconds. Delete the check images.

## 5. Deliver

Give the user the MP4's path (show it if your environment can display files). It has no sound, ready for music or a
voiceover. Offer one variation (another ending, another scene).

## No browser here? (for example the Claude app's sandbox)

If the setup check can't get a browser running, write the animation as a page instead:
`python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" stick-<topic>.json --html stick-<topic>.html`. The page plays in any
browser (show it as an artifact if you can). Tell the user the MP4 needs Claude Code on a computer, or a screen recording
of the page.
