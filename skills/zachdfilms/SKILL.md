---
name: zachdfilms
description: Turns a what-if question into a 3D animated what-if explainer clip (Seedance 2.5 via the Higgsfield connector, 1080p). Use for /zachdfilms or /ZachDFilms, or any ask for a what-if 3D explainer.
license: MIT
---

# /zachdfilms: any what-if question as a 3D animated explainer

The user asks a what-if question ("What if the Moon disappeared?", "What if Earth had rings like Saturn?"). You write the
shot, generate it with Seedance 2.5 on Higgsfield at 1080p, put the question on it in the big white-and-yellow explainer
style, and hand back a 5-second vertical MP4 with sound. (Named after the photoreal what-if explainer style it imitates;
not affiliated with any creator.)

`${CLAUDE_SKILL_DIR}` below is this skill's folder (the one this SKILL.md is in). If your environment doesn't fill it in,
use that folder's path. Save everything in the user's current folder, or the folder they name. `<slug>` below means a
short name from the question, like `moon-disappeared`.

## 0. Check you can generate

You need the **Higgsfield connector** (its tools include `generate_video`, `jobs_wait` and `balance`; they may need loading
first). If it isn't there, stop and tell the user how to add it: in the Claude app or on claude.ai, Settings →
Connectors → find Higgsfield → Connect; in Claude Code, connectors added on claude.ai appear when you're signed in with
the same account, or run `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai` and sign in through
`/mcp`. Offer them the prompt you'd use (step 1) so they can paste it into Higgsfield themselves (Seedance 2.5, 9:16,
1080p, 5 s) and come back with the clip for step 4. You also need ffmpeg for step 4 (macOS: `brew install ffmpeg`, or
`python3 -m pip install imageio-ffmpeg`).

## 1. Write the title and the shot

**Title**: the question as two short lines of similar length, separated by `|`, the second ending with the question mark:
`What if the Moon|disappeared?`, `What if Earth had|rings like Saturn?`.

**Prompt**: one dramatic, physically plausible event, shown from start to end in 5 seconds. Fill this recipe:

```
Hyper-realistic 3D animated science explainer, high-end CGI render in the style of viral what-if explainer shorts.
Vertical frame; keep the top fifth of the frame dark, empty sky or space. [WHERE WE ARE: what fills the frame first,
concrete and physical, in one or two sentences.] [THE CHANGE: the one thing that happens, in time order, with what it
does to things around it.] [CAMERA: one simple move: slow push-in, slow orbit, a tracking shot.] Dramatic rim light,
crisp photoreal detail, cinematic. No text, no people, no logos. Sound: [what you'd hear: deep rumble, whoosh,
crackle], no music, no voices.
```

Example ("What if the Moon disappeared?"):

```
Hyper-realistic 3D animated science explainer, high-end CGI render in the style of viral what-if explainer shorts.
Vertical frame; keep the top fifth of the frame dark, empty space. The curved blue horizon of planet Earth glows across
the bottom of the frame with thin atmosphere and white clouds; the full Moon hangs large in the black starry sky above
it, sharply lit by the sun, every crater visible. Glowing orange cracks spread across the Moon's grey surface, then it
bursts apart into thousands of rocky fragments and fine grey dust that drift outward in slow motion and thin out into
nothing, leaving an empty dark sky above the Earth. Slow steady camera push-in toward the Moon. Dramatic rim light,
crisp photoreal detail, cinematic. No text, no people, no logos. Sound: a deep cracking rumble and a slow whoosh of
debris, no music, no voices.
```

Keep people out of the shot (faces and bodies are where generated video looks fake), and keep it to one event.

## 2. Price it, then generate (always 1080p)

1. Price it and check the balance: call `generate_video` with `get_cost: true` and the same params as below (it returns
   the credits, about 80 for 5 s at 1080p), and `balance`. If there aren't enough credits, stop and tell the user (they can
   top up on Higgsfield). Tell the user the cost in one line. Typing /zachdfilms is their go-ahead for one shot; ask first
   only for anything bigger (the three-shot version, a retry).
2. Generate. The tool takes its settings wrapped in `params`, and no project or folder is needed (leave `folder_id` out):

```json
{"params": {"model": "seedance_2_5", "mode": "t2v", "prompt": "<the prompt>", "aspect_ratio": "9:16",
            "resolution": "1080p", "duration": 5, "generate_audio": true}}
```

   Always 1080p for the result (never a 480p draft). The answer lists the job: `{"results": [{"id": "<job id>", "status":
   "pending", ...}]}`. If the tool answers with a question instead (for example whether to use free or unlimited
   generations), put that question to the user and call again with their answer. Don't resubmit after a timeout: reuse the
   job ID it gave you.
3. Wait: call `jobs_wait` with `{"jobs": [{"index": 0, "job_id": "<job id>"}], "timeout_seconds": 15}` and call it again
   while it says `in_progress` (each call waits up to 15 s; a 1080p shot usually takes 2-4 minutes, about 10 calls). When
   the job is `completed`, the video's URL is in its `result_url`.

**Longer version** (only when the user asks for a longer or full explainer, and after they OK three times the cost): three
5-second shots (the setup, the change, the aftermath), each with its own prompt and a caption line of up to ~6 words,
started together with `generate_video_batch` at 1080p and waited for with one `jobs_wait` call listing all three jobs.

## 3. Download

```bash
curl -L -o zach-<slug>-raw.mp4 "<result_url>"
```

## 4. Put the question on it

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/finish.py" --clip zach-<slug>-raw.mp4 --title "What if the Moon|disappeared?" --out zach-<slug>.mp4
```

It sets the title (white, the second line yellow, heavy outline, over a soft dark band so it reads on bright shots),
keeps Seedance's sound and levels it for phones, and writes 1080x1920 H.264. For three shots:
`--clip a.mp4 --clip b.mp4 --clip c.mp4 --caption "" --caption "Tides would shrink" --caption "Nights go dark"` (one
`--caption` per clip, in order; the title sits on the first clip).

## 5. Check it, then deliver

Look at a frame (`ffmpeg -v error -ss 2 -i zach-<slug>.mp4 -frames:v 1 zach-<slug>-check.png`): the shot shows the
question's event and the title reads cleanly. If the generation missed (wrong event, garbled scene), say so, offer a
rewritten prompt and ask before spending credits on a second try. Then give the user the MP4's path (show it if your
environment can display files) and the Higgsfield job ID. Delete the check image; keep the raw clip only if they want it
(it can be downloaded again from the same URL).

## No downloads here? (for example the Claude app's sandbox)

If you can generate but can't download the video into your workspace (no network access), give the user the video link
and the title text, and tell them the finished version with the title needs Claude Code on a computer.
