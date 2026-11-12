---
name: map-route
description: Makes a 3D map video with the real route drawing itself between two places (1080x1920 MP4). Use for /map-route with two places, or any ask to animate a route, trip or directions.
license: MIT
---

# /map-route: two places, a 3D map, the route drawing itself

The user names two places ("Times Square to Empire State", "London to Paris", "my hotel in Lisbon to the airport"). You
find them, get the real route, check a frame, render the video and hand back a silent MP4 (about 4.5 seconds).

`${CLAUDE_SKILL_DIR}` below is this skill's folder (the one this SKILL.md is in). If your environment doesn't fill it in,
use that folder's path. Save everything in the user's current folder, or the folder they name. This skill needs an
internet connection (map searches, routes and map tiles).

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

## 1. Find the places and the route

Make each place specific enough for a map search: add the city (and the country if it's ambiguous):
"Empire State" → "Empire State Building, New York". Then:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/route.py" "Times Square, New York" "Empire State Building, New York" \
  --labels "Times Square" "Empire State Building" --out map-<from>-<to>.json
```

- `--labels`: the short names shown on the pins and the card.
- `--mode`: `auto` (default: walk under 4 km in a straight line, drive under 900 km, a flight beyond that or when no
  road connects them), `walk`, `bike`, `drive`, `fly`. Use what the user asked for ("drive from...", "fly to..."). Two
  sights in the same city are usually a walk: pass `--mode walk` up to ~5 km unless they said otherwise.
- `--style`: `light` (default), `dark`, `color`. `--title "..."` replaces the "A → B" line on the card.
- `--units`: `auto` (miles when both places are in the US or UK), `metric`, `imperial`. `--size`: `1080x1920` (default),
  `1080x1080`, `1920x1080`.

It prints what it found. **Check the `from` and `to` lines are the places the user meant** (the right city, the right
building; a museum may show as one of its entrances, which is fine). If not, make the search text more specific and run
it again, a few times at most: these are free community servers, one request at a time.

Places can also be coordinates (`"40.7580,-73.9855"`) or street addresses.

## 2. Check the last frame

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" map-<from>-<to>.json --still end --out map-<from>-<to>-check.png
```

Look at the image (about 10 seconds to make): both pins and their names on screen, the route clear, the card right
(distance, time, mode)?

## 3. Render the video

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/render.py" map-<from>-<to>.json --out map-<from>-<to>.mp4
```

About 30-60 seconds: every frame waits for the real map tiles. If a render comes out black or blank, add `--no-gpu`.
Delete the check image.

## 4. Deliver

Give the user the MP4's path (show it if your environment can display files), with the distance and time it shows. It has
no sound. Offer one variation (the dark style, another mode, a longer version).

The spec is plain JSON: you can change the pin names (`from.name`, `to.name`), `title`, `subtitle` (replaces the distance
line), `style`, `color` (the route's colour) or `duration` (seconds, default ~4.5; a longer one slows the whole move
down, e.g. 7 for a calmer version) and render again without searching again.

## Without internet access

The map needs live map tiles and the routing servers. In a sandbox without network access (or without a browser), tell
the user so instead of drawing a made-up map.

Map data © OpenStreetMap contributors (ODbL), tiles by OpenFreeMap (OpenMapTiles schema), routes by OSRM on the FOSSGIS
servers. The attribution line stays on the video.
