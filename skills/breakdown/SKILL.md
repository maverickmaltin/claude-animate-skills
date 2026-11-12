---
name: breakdown
description: Pulls a product apart in 3D and labels every piece inside, as a 1080x1920 MP4. Use for /breakdown with a product photo or name, or any ask for an exploded view or teardown animation.
license: MIT
---

# /breakdown: your product, pulled apart, every piece labelled

The user attaches a product photo and/or names a product. You work out what it's made of, describe it as simple 3D parts
(sizes in millimetres), check two frames, render it turning, pulling apart and labelling itself, and hand back a silent
MP4 (about 6 seconds).

`${CLAUDE_SKILL_DIR}` below is this skill's folder (the one this SKILL.md is in). If your environment doesn't fill it in,
use that folder's path. Save everything in the user's current folder, or the folder they name. The 3D page loads three.js
from the internet, so it needs a connection.

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

## 1. Work out the product

- From the photo: overall shape, proportions, colours and finishes (glossy glass, brushed metal, matte plastic, fabric),
  and the layout of visible details (camera lenses, buttons, ports). Don't reproduce brand logos.
- Its real main parts, in assembly order from one side to the other: 5-9 parts worth labelling (cover, screen, frame,
  battery, board, chip, speaker, driver, cushion...). Use what this kind of product really contains; if unsure about a
  specific model, use the parts its category always has, and don't make up exotic ones.
- Real approximate sizes in mm (a phone is ~72 x 150 mm and 8 mm thick; a full keyboard ~440 x 130 mm).

## 2. Write the spec

Save `breakdown-<product>.json`. Each part is a simple shape placed where it sits in the assembled product; `level` says
how far it travels when the product comes apart (0 stays put, 1 moves one step, 2 two steps; parts with the same level
move together; halves like 3.5 work). Example (`examples/smartphone.json`, shortened):

```json
{
  "title": "Inside a smartphone",
  "theme": "dark",
  "parts": [
    {"name": "Cover glass", "shape": "slab", "size": [72, 0.7, 150], "radius": 10.5, "material": "glass", "y": 0, "level": 0},
    {"name": "Display", "shape": "slab", "size": [69, 0.7, 147], "radius": 9, "material": "black", "color": "#232428", "y": 0.8, "level": 1},
    {"name": "Frame", "shape": "frame", "size": [72, 7.4, 150], "radius": 10.5, "wall": 2.5, "material": "aluminum", "y": 0.9, "level": 2},
    {"name": "Battery", "shape": "slab", "size": [62, 4, 86], "radius": 5, "material": "battery", "text": "Li-ion|5,000 mAh", "pos": [0, 2, 24], "level": 3},
    {"name": "Logic board", "shape": "slab", "size": [62, 1, 44], "radius": 4, "material": "pcb", "pos": [0, 2, -48], "level": 3},
    {"name": "Cameras", "shape": "lens", "radius": 4.6, "size": [9.2, 4.2, 9.2], "copies": [[-23.2, -62.2], [-23.2, -45.5], [-8, -53.8]], "y": 6.6, "level": 4},
    {"name": "Back glass", "shape": "slab", "size": [72, 0.9, 150], "radius": 10.5, "material": "glass-tint", "color": "#3d5571", "y": 8.4, "level": 5}
  ]
}
```

**Coordinates**: `size` is `[width x, height y, depth z]` in mm; `y` is up. `pos: [x, y, z]` (or just `"y"`) is where the
part's bottom centre sits in the assembled product. Parts may overlap slightly; that's fine.

**Shapes**: `slab` (rounded rectangle plate; `radius` = corner radius), `frame` (a slab with a hole; `wall` thickness),
`box` (sharp corners), `cylinder`/`disc` (`radius`, height = `size[1]`), `ring` (`radius`, `inner`), `lens` (a camera
lens with its metal ring), `sphere` (scaled by `size`), `capsule`, `cone` (`radiusTop`), `torus`/`cushion` (`radius`,
`tube`: ear cushions, O-rings), `lathe` (`profile`: `[[radius, y], ...]` spun around the vertical axis: bottles, cups,
knobs, speaker cones). `rot: [x, y, z]` degrees turns a part (e.g. `[90, 0, 0]` stands a cylinder on its side, `[0, 90,
0]` turns a slab so its printed text reads along the other side).

**Repeats**: `copies: [[x, z], ...]` (or `[x, y, z]`) places the same part several times (cameras, screws, buttons);
`grid: {"nx": 14, "nz": 5, "pitch": 19}` lays out a grid (keycaps, cells, LEDs).

**Materials**: `glass` (clear), `glass-tint` (coloured glass), `aluminum`, `steel`, `gold`, `copper`, `black`, `white`,
`plastic` (any `color`), `ceramic`, `rubber`, `foam`, `fabric` (mesh grille), `wood`, `leather`, `pcb` (green circuit
board), `chip`, `battery` (dark cell; `text` is printed on it, `|` for new lines), `coil` (copper wireless-charging coil),
`lens`, `screen` (a lit display), `magnet`, `emissive` (glows). `color` (hex) tints most of them. `text` prints a label
on a slab's top face. Studio lighting brightens colours a little: compare the first check frame with the photo and darken
the `color` if it looks washed out.

**The user's photo**: use it to get the shape, colours and layout right. If it shows a flat face straight on (a phone's
back or screen, a card, a lid), you can also map it onto that part: `"photo": "path/to/photo.jpg"` at the top level, then
`"texture": "photo"` on the part, with `"crop": [x0, y0, x1, y1]` (0-1 fractions of the photo) around that face. For an
angled or perspective shot, use colours and layout only.

**Labels**: each part is labelled with its `name` (keep names short: up to ~14 characters stay full size);
`"label": "Other text"` changes it, `"label": false` hides it (use that for small decoration parts so only 5-9 labels
show).

**The view**: the product turns on a turntable: its angle in radians is `spin - spinSpeed × seconds` (defaults 0.95 and
0.07, so it ends around a three-quarter view). For long flat things where parts hide each other, end side-on: e.g.
`"spin": 1.9, "spinSpeed": 0.06`. `elevation0`/`elevation1` are the camera's height in degrees (38 → 24 by default).

Other fields: `title` (e.g. "Inside a ..."), `subtitle`, `theme` (`dark` default, `light`), `axis` (`"y"` pulls apart
upward, default; `"x"` or `"z"` pulls apart sideways, for long things like pens, bottles on their side, headphones),
`gap` (mm between levels; default ~19% of the product's size), `explode: [x, y, z]` on a part (its own travel in mm,
instead of its level), `apartAt` (seconds; default 1.5), `size`, `duration` (default ~6-7 s, enough to read the labels),
`fps`. A second example: `examples/mechanical-keyboard.json`.

## 3. Check two frames

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" breakdown-<product>.json --still 0.5 --out breakdown-<product>-check1.png
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" breakdown-<product>.json --still end --out breakdown-<product>-check2.png
```

`--still` takes seconds, or `end`. The first is the assembled product: does it look like the product (shape, proportions,
colours)? The second is the exploded view with labels: parts in a sensible order, nothing hidden inside something else,
each label's dot on its part, labels readable. Fix sizes, positions, levels or the view and check again (two or three
rounds is normal).

## 4. Render the video

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" breakdown-<product>.json --out breakdown-<product>.mp4
```

About 10-20 seconds. If a 3D render comes out black, add `--no-gpu`. Delete the check images.

## 5. Deliver

Give the user the MP4's path (show it if your environment can display files). It has no sound. Say in one line that the
parts are a simplified model of their product, and offer one variation (the light theme, a part renamed).

## No browser here? (for example the Claude app's sandbox)

If the setup check can't get a browser running, write the animation as a page instead:
`python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" breakdown-<product>.json --html breakdown-<product>.html`. The page plays
in any browser (show it as an artifact if you can). Tell the user the MP4 needs Claude Code on a computer, or a screen
recording of the page.
